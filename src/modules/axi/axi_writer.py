from nmigen import *
from nmigen.lib.fifo import SyncFIFO

from modules.axi.axi import AxiInterface, BurstType
from util.bundle import Bundle


class AddressGenerator(Elaboratable):
    def __init__(self, buffer_base_list, max_buffer_size, addr_bits, inc=16):
        self.buffer_base_list = buffer_base_list
        self.max_buffer_size = max_buffer_size
        self.inc = inc

        self.request = Signal()  # in
        self.change_buffer = Signal()  # in
        self.addr = Signal(addr_bits, reset=buffer_base_list[0])  # out

        self.valid = Signal(reset=1)  # out
        self.done = Signal()  # in
        self.lol = Signal(32)

    def elaborate(self, platform):
        m = Module()

        num_buffers = len(self.buffer_base_list)
        base_addrs = Array(self.buffer_base_list)
        current_buffer = Signal(range(num_buffers))

        with m.If(~self.valid):
            with m.If(self.change_buffer):
                m.d.sync += self.addr.eq(base_addrs[current_buffer + 1])
                m.d.sync += current_buffer.eq(current_buffer + 1)
                m.d.sync += self.valid.eq(1)
            with m.Elif(self.request & ((self.addr - base_addrs[current_buffer] + self.inc) <= self.max_buffer_size)):
                m.d.sync += self.addr.eq(self.addr + self.inc)
                m.d.sync += self.valid.eq(1)

        with m.If(self.done):
            m.d.sync += self.valid.eq(0)

        return m


class AxiHpWriter(Elaboratable):
    def __init__(self, axi_slave: AxiInterface, buffer_base_list, max_buffer_size=0x4000_0000, fifo_depth=64,
                 burst_length=16):
        assert not axi_slave.is_lite
        assert not axi_slave.is_master
        self.fifo_depth = fifo_depth
        self.burst_length = burst_length
        self.word_bytes = int(axi_slave.data_bits / 4)

        self.axi_slave = axi_slave
        self.axi = AxiInterface.like(axi_slave, master=True)
        self.address_generator = AddressGenerator(buffer_base_list, max_buffer_size, self.axi.addr_bits,
                                                  inc=int(burst_length * self.word_bytes))

        self.data_valid = Signal()  # input
        self.data = Signal(self.axi.data_bits)  # input
        self.change_buffer = Signal()  # input; only considered, when data_valid is high
        self.ready = Signal()  # output

        self.dropped = Signal(32)  # output; diagnostics
        self.error = Signal()  # output; diagnostics

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.axi.connect_slave(self.axi_slave)

        address_generator = m.submodules.address_generator = self.address_generator
        addr_fifo = m.submodules.addr_fifo = SyncFIFO(width=self.axi.addr_bits, depth=self.fifo_depth)

        # we fill the input data plus the addr change bit in the data fifo. this gives us a bit of lookahead to schedule
        # the axi bursts
        class PayloadPlusChangeBuffer(Bundle):
            def __init__(self, payload: Signal, change_buffer: Signal):
                super().__init__()
                self.payload = payload
                self.change_buffer = change_buffer

            @staticmethod
            def like(signal):
                return PayloadPlusChangeBuffer(Signal(len(signal) - 1), Signal(1))

        data_fifo = m.submodules.data_fifo = SyncFIFO(width=self.axi.data_bits + 1, depth=self.fifo_depth)
        m.d.comb += self.ready.eq(data_fifo.w_rdy)
        with m.If(~self.ready & self.data_valid):
            m.d.sync += self.dropped.eq(self.dropped + 1)

        with m.If(self.data_valid & self.ready):
            m.d.sync += data_fifo.w_data.eq(PayloadPlusChangeBuffer(self.data, self.change_buffer))
            m.d.sync += data_fifo.w_en.eq(1)
        with m.Else():
            m.d.sync += data_fifo.w_en.eq(0)

        # we want the address fifo to be always filled with addresses for the current buffer; when we do a buffer
        # change, we flush that fifo
        with m.If(~address_generator.valid & ~self.change_buffer):
            m.d.sync += address_generator.request.eq(1)
        with m.Else():
            m.d.sync += address_generator.request.eq(0)

        with m.If(address_generator.valid & ~addr_fifo.w_en):
            m.d.sync += addr_fifo.w_en.eq(1)
            m.d.sync += addr_fifo.w_data.eq(address_generator.addr)
            m.d.sync += address_generator.done.eq(1)
        with m.Else():
            m.d.sync += addr_fifo.w_en.eq(0)
            m.d.sync += address_generator.done.eq(0)

        # normally a transaction is only triggered when there are 16 data words to be written. This is not possible if
        # we are doing a buffer change so then we do a "flush" and produce a transaction that is also 16 long
        # (not optimal but doesnt matter much since a buffer change doesnt happen too often) and set
        # `axi.write_data.byte_strobe` to '0000' for the unused transfers of the burst.
        burst_position = Signal(range(self.burst_length+1))
        m.d.comb += self.axi.write_response.ready.eq(1)
        with m.FSM():
            with m.State("IDLE"):
                with m.If((addr_fifo.level >= 1) & (data_fifo.level >= 16)):
                    # we are doing a full transaction
                    m.next = "ADDRESS_0"
            with m.State("ADDRESS_0"):
                m.d.comb += addr_fifo.r_en.eq(1)
                m.next = "ADDRESS_1"
            with m.State("ADDRESS_1"):
                m.d.comb += self.axi.write_address.value.eq(addr_fifo.r_data)
                m.d.comb += self.axi.write_address.burst_len.eq(self.burst_length - 1)
                m.d.comb += self.axi.write_address.burst_type.eq(BurstType.INCR)
                m.d.comb += self.axi.write_address.valid.eq(1)
                with m.If(self.axi.write_address.ready):
                    m.next = "TRANSFER_DATA"
            with m.State("TRANSFER_DATA"):
                with m.If(burst_position < self.burst_length):
                    bundle = PayloadPlusChangeBuffer.like(data_fifo.r_data)
                    m.d.comb += bundle.eq(data_fifo.r_data)

                    with m.If(bundle.change_buffer):
                        m.next = "FLUSH"

                    m.d.comb += self.axi.write_data.value.eq(bundle.payload)
                    m.d.comb += self.axi.write_data.valid.eq(1)
                    with m.If(self.axi.write_data.ready):
                        m.d.comb += data_fifo.r_en.eq(1)
                        m.d.sync += burst_position.eq(burst_position + 1)
                with m.Else():
                    m.d.sync += burst_position.eq(0)
                    m.next = "IDLE"
                    with m.If((~data_fifo.r_rdy)):
                        # we have checked this earlier so this should never be a problem
                        m.d.sync += self.error.eq(1)
            with m.State("FLUSH"):
                # TODO: implement
                pass

        return m
