from nmigen import *

from lib.bus.ring_buffer import RingBufferAddressStorage
from lib.bus.stream.stream import PacketizedStream, Stream
from lib.peripherals.csr_bank import StatusSignal, ControlSignal
from util.nmigen_misc import with_reset
from .axi_endpoint import AddressStream, BurstType
from .util import get_axi_master_from_maybe_slave
from ..stream.fifo import BufferedSyncStreamFIFO
from ..stream.stream_transformer import StreamTransformer
from ...data_structure.bundle import DOWNWARDS


class AxiBufferWriter(Elaboratable):
    def __init__(
            self,
            ringbuffer: RingBufferAddressStorage,
            input: PacketizedStream,
            axi_slave=None,
            fifo_depth=32, max_burst_length=16
    ):
        self.ringbuffer = ringbuffer

        assert hasattr(input, "last")
        self.input = input

        self.axi_slave = axi_slave

        self.fifo_depth = fifo_depth
        self.max_burst_length = max_burst_length
        self.enable = ControlSignal(reset=1)
        self.flush = ControlSignal()
        self.axi_address_ready = StatusSignal()
        self.axi_data_ready = StatusSignal()

    def elaborate(self, platform):
        m = Module()

        axi = get_axi_master_from_maybe_slave(self.axi_slave, m, platform)
        assert len(self.input.payload) <= axi.data_bits

        wr = with_reset(m, self.flush)

        input_fifo = m.submodules.input_fifo = BufferedSyncStreamFIFO(self.input, 1)  # This is needed to not form a combinatorial loop: TODO: why?
        commander = m.submodules.commander = wr(AddressGeneratorCommander(input_fifo.output))
        output_fifo = m.submodules.output_fifo = wr(BufferedSyncStreamFIFO(commander.output_data, self.max_burst_length))
        address_generator = m.submodules.address_generator = wr(AddressGenerator(
            commander.output_request_address, self.ringbuffer,
            max_burst=self.max_burst_length, word_width_bytes=axi.data_bytes
        ))
        with m.If(self.enable):
            m.d.comb += axi.write_data.connect_upstream(output_fifo.output, allow_partial=True)
            m.d.comb += axi.write_address.connect_upstream(address_generator.output)

            # we do not currently care about the write responses
            m.d.comb += axi.write_response.ready.eq(1)

        m.d.comb += self.axi_data_ready.eq(axi.write_data.ready)
        m.d.comb += self.axi_address_ready.eq(axi.write_address.ready)

        return m


class AddressGeneratorCommander(Elaboratable):
    def __init__(self, input: PacketizedStream, max_burst_length=16, burst_creation_timeout=31):
        self.burst_creation_timeout = burst_creation_timeout
        self.max_burst_length = max_burst_length
        self.input = input
        self.output_request_address = PacketizedStream(range(max_burst_length - 1), name="request_address")
        self.output_data = input.clone(name="output_data")
        self.output_data.byte_strobe = Signal(len(self.output_data.payload) // 8, reset=-1) @ DOWNWARDS

    def elaborate(self, platform):
        m = Module()

        counter = Signal.like(self.output_request_address.payload)
        timeout_counter = Signal(range(self.burst_creation_timeout))
        with m.If(self.output_data.ready):
            with m.If(self.input.valid):
                m.d.sync += timeout_counter.eq(0)
                m.d.comb += self.output_data.payload.eq(self.input.payload)
                with m.If(self.input.last | (counter == self.max_burst_length - 1)):
                    m.d.comb += self.output_request_address.valid.eq(1)
                    m.d.comb += self.output_request_address.payload.eq(counter)
                    m.d.comb += self.output_request_address.last.eq(self.input.last)
                    with m.If(self.output_request_address.ready):
                        m.d.comb += self.input.ready.eq(1)
                        m.d.comb += self.output_data.valid.eq(1)
                        m.d.comb += self.output_data.last.eq(1)
                        m.d.sync += counter.eq(0)
                with m.Else():
                    m.d.comb += self.output_data.valid.eq(1)
                    m.d.comb += self.input.ready.eq(1)
                    m.d.sync += counter.eq(counter + 1)
            with m.Elif(counter != 0):
                with m.If(timeout_counter == self.burst_creation_timeout):
                    with m.If(self.output_data.ready):  # flush on timeout
                        m.d.comb += self.output_request_address.valid.eq(1)
                        m.d.comb += self.output_request_address.payload.eq(counter)
                        m.d.comb += self.output_request_address.last.eq(0)
                        with m.If(self.output_request_address.ready):
                            m.d.comb += self.output_data.valid.eq(1)
                            m.d.comb += self.output_data.last.eq(1)
                            m.d.comb += self.output_data.byte_strobe.eq(0)
                            m.d.sync += timeout_counter.eq(0)
                            m.d.sync += counter.eq(0)
                with m.Else():
                    m.d.sync += timeout_counter.eq(timeout_counter + 1)

        return m


class AddressGenerator(Elaboratable):
    def __init__(self, request: PacketizedStream, ringbuffer: RingBufferAddressStorage, max_burst, word_width_bytes=8):
        self.word_width_bytes = word_width_bytes
        self.ringbuffer = ringbuffer
        self.current_buffer = StatusSignal(ringbuffer.current_write_buffer.shape())

        # this is pessimistic but we rather allocate larger buffers and _really_ not write anywhere else
        self.max_addrs = Array(addr_base + ringbuffer.buffer_size - (2 * max_burst * word_width_bytes)
                               for addr_base in self.ringbuffer.buffer_base_list)

        # the payload is how much we increment our address, last if we change the buffer
        self.request = request
        self.output = AddressStream(addr_bits=32, lite=False, id_bits=12, data_bytes=8)
        self.overflowed_buffers = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        self.output.payload.reset = self.ringbuffer.buffer_base_list[0]

        m.d.comb += self.ringbuffer.current_write_buffer.eq(self.current_buffer)
        was_overflow = Signal()
        with StreamTransformer(self.request, self.output, m):
            m.d.comb += self.output.burst_type.eq(BurstType.INCR)
            m.d.comb += self.output.burst_len.eq(self.request.payload)
            with m.If(~self.request.last):
                with m.If((self.output.payload <= self.max_addrs[self.current_buffer])):
                    m.d.sync += self.output.payload.eq(self.output.payload + (self.request.payload + 1) * self.word_width_bytes)
                with m.Elif(~was_overflow):
                    m.d.sync += was_overflow.eq(1)
                    m.d.sync += self.overflowed_buffers.eq(self.overflowed_buffers + 1)
            with m.Else():
                m.d.sync += was_overflow.eq(0)
                with m.If(self.current_buffer < len(self.ringbuffer.buffer_base_list) - 1):
                    m.d.sync += self.current_buffer.eq(self.current_buffer + 1)
                    m.d.sync += self.output.payload.eq(self.ringbuffer.buffer_base_list[self.current_buffer + 1])
                with m.Else():
                    m.d.sync += self.current_buffer.eq(0)
                    m.d.sync += self.output.payload.eq(self.ringbuffer.buffer_base_list[0])

        return m
