from nmigen import *

from lib.bus.stream.fifo import BufferedSyncStreamFIFO
from lib.bus.stream.stream import BasicStream, PacketizedStream


class LastWrapper(Elaboratable):
    """wraps a core that transforms one BasicStream into another BasicStream (with variable latency) and applies the last signal correctly to its output"""

    def __init__(self, input: PacketizedStream, core_producer, last_fifo_depth=1, last_rle_bits=10):
        self.last_fifo_depth = last_fifo_depth
        self.last_rle_bits = last_rle_bits
        assert hasattr(input, "last")
        self.input = input

        self.core_input = BasicStream(input.payload.shape())
        self.core = core_producer(self.core_input)
        self.core_output = self.core.output

        self.output = PacketizedStream(len(self.core_output.payload))

    def elaborate(self, platform):
        m = Module()

        core = m.submodules.core = self.core

        last_fifo_input = BasicStream(self.last_rle_bits)
        last_fifo = m.submodules.last_fifo = BufferedSyncStreamFIFO(last_fifo_input, self.last_fifo_depth)

        rle_input_counter = Signal(self.last_rle_bits)
        m.d.comb += self.input.ready.eq(last_fifo_input.ready & self.core_input.ready)
        with m.If(last_fifo_input.ready & self.core_input.ready & self.input.valid):
            m.d.comb += self.core_input.valid.eq(1)
            m.d.comb += self.core_input.payload.eq(self.input.payload)
            with m.If(~self.input.last):
                with m.If(rle_input_counter == (2 ** self.last_rle_bits - 1)):
                    m.d.comb += last_fifo_input.valid.eq(1)
                    m.d.comb += last_fifo_input.payload.eq(rle_input_counter)
                    m.d.sync += rle_input_counter.eq(0)
                with m.Else():
                    m.d.sync += rle_input_counter.eq(rle_input_counter + 1)
            with m.Else():
                m.d.comb += last_fifo_input.valid.eq(1)
                m.d.comb += last_fifo_input.payload.eq(rle_input_counter)
                m.d.sync += rle_input_counter.eq(0)

        rle_output_counter = Signal(self.last_rle_bits)
        with m.If(self.output.ready & self.core_output.valid & last_fifo.output.valid):
            m.d.comb += self.output.valid.eq(1)
            m.d.comb += self.core_output.ready.eq(1)
            m.d.comb += self.output.payload.eq(self.core_output.payload)
            with m.If(rle_output_counter == last_fifo.output.payload):
                m.d.comb += last_fifo.output.ready.eq(1)
                with m.If(rle_output_counter != (2 ** self.last_rle_bits - 1)):
                    m.d.comb += self.output.last.eq(1)
                m.d.sync += rle_output_counter.eq(0)
            with m.Else():
                m.d.sync += rle_output_counter.eq(rle_output_counter + 1)

        return m
