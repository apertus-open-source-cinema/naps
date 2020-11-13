from nmigen import *

from lib.bus.ring_buffer import RingBufferAddressStorage
from lib.bus.stream.stream import PacketizedStream
from lib.peripherals.csr_bank import StatusSignal, ControlSignal
from util.nmigen_misc import with_reset
from .axi_endpoint import AddressStream, BurstType
from .util import get_axi_master_from_maybe_slave
from ..stream.fifo import BufferedSyncStreamFIFO
from ..stream.stream_transformer import StreamTransformer


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

    def elaborate(self, platform):
        m = Module()

        self.output.payload.reset = self.ringbuffer.buffer_base_list[0]

        m.d.comb += self.ringbuffer.current_write_buffer.eq(self.current_buffer)
        with StreamTransformer(self.request, self.output, m):
            m.d.comb += self.output.burst_type.eq(BurstType.INCR)
            m.d.comb += self.output.burst_len.eq(self.request.payload)
            with m.If(~self.request.last):
                m.d.sync += self.output.payload.eq(self.output.payload + (self.request.payload + 1) * self.word_width_bytes)
            with m.Elif((self.output.payload <= self.max_addrs[self.current_buffer])):
                with m.If(self.current_buffer < len(self.ringbuffer.buffer_base_list) - 1):
                    m.d.sync += self.current_buffer.eq(self.current_buffer + 1)
                    m.d.sync += self.output.payload.eq(self.ringbuffer.buffer_base_list[self.current_buffer + 1])
                with m.Else():
                    m.d.sync += self.current_buffer.eq(0)
                    m.d.sync += self.output.payload.eq(self.ringbuffer.buffer_base_list[0])

        return m


class AddressGeneratorCommander(Elaboratable):
    def __init__(self, input: PacketizedStream, max_burst_length=16, burst_creation_timeout=31):
        self.burst_creation_timeout = burst_creation_timeout
        self.max_burst_length = max_burst_length
        self.input = input
        self.output_request_address = PacketizedStream(range(max_burst_length - 1), name="request_address")
        self.output_data = input.clone(name="output_data")

    def elaborate(self, platform):
        m = Module()

        has_next_output_data = Signal()
        next_output_data_put = Signal()
        next_output_data_taken = Signal()
        m.d.sync += has_next_output_data.eq(has_next_output_data + next_output_data_put - next_output_data_taken)
        next_output_data_payload = Signal.like(self.input.payload)
        next_output_data_last = Signal()

        counter = Signal.like(self.output_request_address.payload)
        timeout_counter = Signal(range(self.burst_creation_timeout))
        with m.If(self.output_data.ready):
            with m.If(has_next_output_data & next_output_data_put):
                m.d.comb += next_output_data_taken.eq(1)
                m.d.comb += self.output_data.valid.eq(1)
                m.d.comb += self.output_data.payload.eq(next_output_data_payload)
                m.d.comb += self.output_data.last.eq(next_output_data_last)

            with m.If(self.input.valid):
                m.d.sync += timeout_counter.eq(0)
                with m.If(self.input.last | (counter == self.max_burst_length - 1)):
                    with m.If(self.output_request_address.ready):
                        m.d.comb += self.input.ready.eq(1)
                        m.d.sync += counter.eq(0)

                        m.d.comb += self.output_request_address.valid.eq(1)
                        m.d.comb += self.output_request_address.payload.eq(counter)
                        m.d.comb += self.output_request_address.last.eq(self.input.last)

                        m.d.comb += next_output_data_put.eq(1)
                        m.d.sync += next_output_data_last.eq(1)
                        m.d.sync += next_output_data_payload.eq(self.input.payload)
                with m.Else():
                    m.d.comb += self.input.ready.eq(1)
                    m.d.sync += counter.eq(counter + 1)

                    m.d.comb += next_output_data_put.eq(1)
                    m.d.sync += next_output_data_last.eq(0)
                    m.d.sync += next_output_data_payload.eq(self.input.payload)
            with m.Elif(has_next_output_data):
                with m.If(timeout_counter == self.burst_creation_timeout):
                    with m.If(self.output_request_address.ready & self.output_data.ready):  # flush on timeout
                        m.d.comb += self.output_request_address.valid.eq(1)
                        m.d.comb += self.output_request_address.payload.eq(counter - 1)
                        m.d.comb += self.output_request_address.last.eq(0)

                        m.d.comb += self.output_data.valid.eq(1)
                        m.d.comb += self.output_data.last.eq(1)
                        m.d.comb += self.output_data.payload.eq(next_output_data_payload)
                        m.d.sync += timeout_counter.eq(0)
                        m.d.sync += counter.eq(0)
                        m.d.sync += has_next_output_data.eq(0)
                with m.Else():
                    m.d.sync += timeout_counter.eq(timeout_counter + 1)

        return m


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
        self.force_flush = ControlSignal()

    def elaborate(self, platform):
        m = Module()

        axi = get_axi_master_from_maybe_slave(self.axi_slave, m, platform)
        assert len(self.input.payload) <= axi.data_bits

        input_clone = self.input.clone()  # we do this to avoid hierarchy flattening
        m.d.comb += input_clone.connect_upstream(self.input)

        wr = with_reset(m, self.force_flush)

        input_fifo = m.submodules.input_fifo = wr(BufferedSyncStreamFIFO(input_clone, self.fifo_depth))
        commander = m.submodules.commander = wr(AddressGeneratorCommander(input_fifo.output))

        output_fifo = m.submodules.output_fifo = wr(BufferedSyncStreamFIFO(commander.output_data, 32))
        m.d.comb += axi.write_data.connect_upstream(output_fifo.output, allow_partial=True)

        address_fifo = m.submodules.address_fifo = wr(BufferedSyncStreamFIFO(commander.output_request_address, 100))
        address_generator = m.submodules.address_generator = wr(AddressGenerator(
            address_fifo.output, self.ringbuffer,
            max_burst=self.max_burst_length, word_width_bytes=axi.data_bytes
        ))
        m.d.comb += address_generator.output.connect_downstream(axi.write_address)

        with m.If(self.force_flush):
            m.d.comb += self.input.ready.eq(0)
            m.d.comb += input_clone.valid.eq(0)

            m.d.comb += axi.write_data.valid.eq(1)
            m.d.comb += axi.write_response.valid.eq(0)

        # we do not currently care about the write responses
        m.d.comb += axi.write_response.ready.eq(1)

        return m
