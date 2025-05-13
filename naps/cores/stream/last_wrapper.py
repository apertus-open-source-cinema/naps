from amaranth import *
from amaranth.lib import wiring, stream
from amaranth.lib.wiring import Component, In, Out

from naps import StatusSignal, Packet
from . import BufferedSyncStreamFIFO


__all__ = ["LastWrapper"]

class LastWrapper(Component):
    """wraps a core that transforms one BasicStream into another BasicStream (with variable latency) and applies the last signal correctly to its output
    This core should be connected like this:
    input -> [ Last Wrapper ] -> Output
                ↳ [core] ↝
    """

    # TODO: if we have a last_fifo_depth of 2 we cant do formal anymore because of this yosys bug:
    #       https://github.com/YosysHQ/yosys/issues/2577
    def __init__(self, to_core_shape,  from_core_shape, last_fifo_depth=3, last_rle_bits=10):
        super().__init__(wiring.Signature({
            "input": In(stream.Signature(Packet(to_core_shape))),
            "to_core": Out(stream.Signature(to_core_shape)),
            "from_core": In(stream.Signature(from_core_shape)),
            "output": Out(stream.Signature(Packet(from_core_shape)))
        }))
        self.last_fifo_depth = last_fifo_depth
        self.last_rle_bits = last_rle_bits

        self.error = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        last_fifo = m.submodules.last_fifo = BufferedSyncStreamFIFO(self.last_rle_bits, self.last_fifo_depth)

        overflow_word = (2 ** self.last_rle_bits - 1)

        rle_input_counter = StatusSignal(self.last_rle_bits)
        with m.If(self.input.valid & last_fifo.input.ready):
            m.d.comb += self.to_core.valid.eq(1)
            m.d.comb += self.to_core.p.eq(self.input.p.p)

            with m.If(self.to_core.ready):
                m.d.comb += self.input.ready.eq(1)

                with m.If(self.input.p.last | (rle_input_counter == overflow_word - 1)):
                    with m.If(~self.input.p.last & (rle_input_counter == overflow_word - 1)):
                        m.d.comb += last_fifo.input.p.eq(overflow_word)
                    with m.Else():
                        m.d.comb += last_fifo.input.p.eq(rle_input_counter)
                    m.d.comb += last_fifo.input.valid.eq(1)
                    m.d.sync += rle_input_counter.eq(0)
                with m.Else():
                    m.d.sync += rle_input_counter.eq(rle_input_counter + 1)

        rle_output_counter = StatusSignal(self.last_rle_bits)
        with m.If(self.from_core.valid):
            m.d.comb += self.output.valid.eq(1)
            m.d.comb += self.output.p.p.eq(self.from_core.p)

            overflow = (last_fifo.output.p == overflow_word) & (rle_output_counter == (overflow_word - 1))
            with m.If(((rle_output_counter == last_fifo.output.p) | overflow) & last_fifo.output.valid):
                with m.If(~overflow):
                    m.d.comb += self.output.p.last.eq(1)
                with m.If(self.output.ready):
                    m.d.sync += rle_output_counter.eq(0)
                    m.d.comb += last_fifo.output.ready.eq(1)
                    m.d.comb += self.from_core.ready.eq(1)
            with m.Elif((rle_output_counter > last_fifo.output.p) & last_fifo.output.valid):
                with m.If(self.output.ready):
                    m.d.comb += self.from_core.ready.eq(1)
                    m.d.sync += self.error.eq(self.error + 1)
            with m.Else():
                with m.If(self.output.ready):
                    m.d.comb += self.from_core.ready.eq(1)
                    m.d.sync += rle_output_counter.eq(rle_output_counter + 1)

        return m
