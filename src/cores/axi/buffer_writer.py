from nmigen import *
from nmigen.lib.fifo import SyncFIFO

from .axi_interface import AxiInterface, BurstType
from cores.csr_bank import StatusSignal
from util.nmigen import nMax, mul_by_pot


class AddressGenerator(Elaboratable):
    def __init__(self, buffer_base_list, max_buffer_size, addr_bits, max_incr):
        self.buffer_base_list = buffer_base_list
        self.max_buffer_size = max_buffer_size
        # this is very pessimistic but we rather allocate larger buffers and _really_ not write anywhere else
        self.max_addrs = Array(addr_base + max_buffer_size - (2 * max_incr) for addr_base in buffer_base_list)

        self.request = Signal()  # in
        self.inc = Signal(range(max_incr+1))
        self.change_buffer = Signal()  # in
        self.addr = Signal(addr_bits, reset=buffer_base_list[0])  # out

        self.valid = Signal(reset=1)  # out
        self.done = Signal()  # in

    def elaborate(self, platform):
        m = Module()

        num_buffers = len(self.buffer_base_list)
        base_addrs = Array(self.buffer_base_list)
        current_buffer = Signal(range(num_buffers))

        with m.If(~self.valid):
            with m.If(self.change_buffer):
                with m.If(current_buffer < len(self.buffer_base_list) - 1):
                    m.d.sync += current_buffer.eq(current_buffer + 1)
                    m.d.sync += self.addr.eq(base_addrs[current_buffer + 1])
                with m.Else():
                    m.d.sync += current_buffer.eq(0)
                    m.d.sync += self.addr.eq(base_addrs[0])
                m.d.sync += self.valid.eq(1)
            with m.Elif(self.request & (self.addr <= self.max_addrs[current_buffer])):
                m.d.sync += self.addr.eq(self.addr + self.inc)
                m.d.sync += self.valid.eq(1)

        with m.If(self.done):
            m.d.sync += self.valid.eq(0)

        return m


class AxiBufferWriter(Elaboratable):
    def __init__(self, axi_slave: AxiInterface, buffer_base_list, max_buffer_size, fifo_depth=32,
                 max_burst_length=16):
        assert not axi_slave.is_lite
        assert not axi_slave.is_master
        self.fifo_depth = fifo_depth
        self.max_burst_length = max_burst_length

        self.axi_slave = axi_slave
        self.axi = AxiInterface.like(axi_slave, master=True)
        self.address_generator = AddressGenerator(buffer_base_list, max_buffer_size, self.axi.addr_bits,
                                                  max_incr=max_burst_length*self.axi.data_bytes)

        self.data_valid = Signal()
        self.data = Signal(self.axi.data_bits)
        self.change_buffer = Signal()  # only considered, when data_valid is high
        self.data_ready = Signal()

        self.dropped = StatusSignal(32)
        self.error = StatusSignal()
        self.state = StatusSignal(32)
        self.written = StatusSignal(32)
        self.burst_position = StatusSignal(range(self.max_burst_length))
        self.data_fifo_level = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.axi.connect_slave(self.axi_slave)

        address_generator = m.submodules.address_generator = self.address_generator

        data_fifo = m.submodules.data_fifo = SyncFIFO(width=self.axi.data_bits + 1, depth=self.fifo_depth, fwft=False)
        m.d.comb += self.data_fifo_level.eq(data_fifo.level)
        m.d.comb += self.data_ready.eq(data_fifo.w_rdy)
        with m.If(~self.data_ready & self.data_valid):
            m.d.sync += self.dropped.eq(self.dropped + 1)

        with m.If(self.data_valid & self.data_ready):
            m.d.sync += data_fifo.w_data.eq(Cat(self.data, self.change_buffer))
            m.d.sync += data_fifo.w_en.eq(1)
        with m.Else():
            m.d.sync += data_fifo.w_en.eq(0)

        # normally a transaction is only triggered when there are 16 data words to be written. This is not possible if
        # we are doing a buffer change so then we do a "flush" and produce a transaction that is also 16 long
        # (not optimal but doesnt matter much since a buffer change doesnt happen too often) and set
        # `axi.write_data.byte_strobe` to '0000' for the unused transfers of the burst.
        m.d.comb += self.axi.write_response.ready.eq(1)
        current_burst_length_minus_one = Signal(range(self.max_burst_length))
        with m.FSM():
            def idle_state():
                # having the idle state in a function is a hack to be able to duplicate its logic
                m.d.comb += self.state.eq(0)
                m.d.sync += self.burst_position.eq(0)
                m.d.comb += address_generator.request.eq(1)
                with m.If(address_generator.valid & data_fifo.r_rdy):
                    # we are doing a full transaction
                    next_burst_length = Signal(range(self.max_burst_length + 1))
                    m.d.comb += next_burst_length.eq(nMax(data_fifo.level, self.max_burst_length))
                    m.d.sync += current_burst_length_minus_one.eq(next_burst_length - 1)
                    m.d.sync += address_generator.inc.eq(mul_by_pot(next_burst_length, self.axi.data_bytes))
                    m.next = "ADDRESS"

            with m.State("IDLE"):
                idle_state()

            with m.State("ADDRESS"):
                m.d.comb += self.state.eq(1)
                m.d.comb += self.axi.write_address.value.eq(address_generator.addr)
                m.d.comb += self.axi.write_address.burst_len.eq(current_burst_length_minus_one)
                m.d.comb += self.axi.write_address.burst_type.eq(BurstType.INCR)
                m.d.comb += self.axi.write_address.valid.eq(1)
                with m.If(self.axi.write_address.ready):
                    m.next = "TRANSFER_DATA"
                    m.d.comb += data_fifo.r_en.eq(1)
                    m.d.comb += address_generator.done.eq(1)

            def last_logic():
                # shared between TRANSFER_DATA and FLUSH
                with m.If(self.burst_position == current_burst_length_minus_one):
                    m.d.comb += self.axi.write_data.last.eq(1)
                    m.next = "IDLE"
                    idle_state()

            with m.State("TRANSFER_DATA"):
                m.d.comb += self.state.eq(2)

                change_buffer = Signal()
                payload = Signal()
                m.d.comb += Cat(payload, change_buffer).eq(data_fifo.r_data)

                with m.If(change_buffer):
                    m.d.comb += self.address_generator.change_buffer.eq(1)
                    m.next = "FLUSH"

                m.d.comb += self.axi.write_data.value.eq(payload)
                m.d.comb += self.axi.write_data.valid.eq(1)

                with m.If(self.axi.write_data.ready):
                    m.d.sync += self.written.eq(self.written + 1)
                    m.d.sync += self.burst_position.eq(self.burst_position + 1)
                    with m.If((self.burst_position < current_burst_length_minus_one) & ~change_buffer):
                        m.d.comb += data_fifo.r_en.eq(1)
                        with m.If((~data_fifo.r_rdy)):
                            # we have checked this earlier so this should never be a problem
                            m.d.sync += self.error.eq(1)
                last_logic()
            with m.State("FLUSH"):
                m.d.comb += self.axi.write_data.byte_strobe.eq(0)
                m.d.comb += self.axi.write_data.valid.eq(1)
                with m.If(self.axi.write_data.ready):
                    m.d.sync += self.written.eq(self.written + 1)
                    m.d.sync += self.burst_position.eq(self.burst_position + 1)
                last_logic()

        return m
