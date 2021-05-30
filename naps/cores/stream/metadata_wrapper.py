from nmigen import *
from naps import BasicStream, PacketizedStream, Stream, DOWNWARDS, StatusSignal
from . import BufferedSyncStreamFIFO, StreamTee, StreamCombiner

__all__ = ["LastWrapper", "GenericMetadataWrapper"]


class LastWrapper(Elaboratable):
    """wraps a core that transforms one BasicStream into another BasicStream (with variable latency) and applies the last signal correctly to its output"""

    # TODO: if we have a last_fifo_depth of 2 we cant do formal anymore because of this yosys bug:
    #       https://github.com/YosysHQ/yosys/issues/2577
    def __init__(self, input: PacketizedStream, core_producer, last_fifo_depth=3, last_rle_bits=10):
        self.last_fifo_depth = last_fifo_depth
        self.last_rle_bits = last_rle_bits
        assert hasattr(input, "last")
        self.input = input

        self.core_input = BasicStream(input.payload.shape())
        self.core = core_producer(self.core_input)
        self.core_output = self.core.output

        self.error = StatusSignal(32)

        self.output = PacketizedStream(len(self.core_output.payload))

    def elaborate(self, platform):
        m = Module()
        m.submodules.core = self.core

        last_fifo_input = BasicStream(self.last_rle_bits)
        last_fifo = m.submodules.last_fifo = BufferedSyncStreamFIFO(last_fifo_input, self.last_fifo_depth)

        overflow_word = (2 ** self.last_rle_bits - 1)

        rle_input_counter = StatusSignal(self.last_rle_bits)
        with m.If(self.input.valid & last_fifo_input.ready):
            m.d.comb += self.core_input.valid.eq(1)
            m.d.comb += self.core_input.payload.eq(self.input.payload)

            with m.If(self.core_input.ready):
                m.d.comb += self.input.ready.eq(1)

                with m.If(self.input.last | (rle_input_counter == overflow_word - 1)):
                    with m.If(~self.input.last & (rle_input_counter == overflow_word - 1)):
                        m.d.comb += last_fifo_input.payload.eq(overflow_word)
                    with m.Else():
                        m.d.comb += last_fifo_input.payload.eq(rle_input_counter)
                    m.d.comb += last_fifo_input.valid.eq(1)
                    m.d.sync += rle_input_counter.eq(0)
                with m.Else():
                    m.d.sync += rle_input_counter.eq(rle_input_counter + 1)

        rle_output_counter = StatusSignal(self.last_rle_bits)
        with m.If(self.core_output.valid):
            m.d.comb += self.output.valid.eq(1)
            m.d.comb += self.output.payload.eq(self.core_output.payload)

            overflow = (last_fifo.output.payload == overflow_word) & (rle_output_counter == (overflow_word - 1))
            with m.If(((rle_output_counter == last_fifo.output.payload) | overflow) & last_fifo.output.valid):
                with m.If(~overflow):
                    m.d.comb += self.output.last.eq(1)
                with m.If(self.output.ready):
                    m.d.sync += rle_output_counter.eq(0)
                    m.d.comb += last_fifo.output.ready.eq(1)
                    m.d.comb += self.core_output.ready.eq(1)
            with m.Elif((rle_output_counter > last_fifo.output.payload) & last_fifo.output.valid):
                with m.If(self.output.ready):
                    m.d.comb += self.core_output.ready.eq(1)
                    m.d.sync += self.error.eq(self.error + 1)
            with m.Else():
                with m.If(self.output.ready):
                    m.d.comb += self.core_output.ready.eq(1)
                    m.d.sync += rle_output_counter.eq(rle_output_counter + 1)

        return m


class GenericMetadataWrapper(Elaboratable):
    def __init__(self, input: BasicStream, core_producer, fifo_depth=128):
        self.fifo_depth = fifo_depth
        self.input = input

        self.core_input = BasicStream(input.payload.shape())
        self.core = core_producer(self.core_input)
        self.core_output = self.core.output

        self.output = self.input.clone()
        self.output.payload = Signal(len(self.core_output.payload)) @ DOWNWARDS

    def elaborate(self, platform):
        m = Module()
        m.submodules.core = self.core
        tee = m.submodules.tee = StreamTee(self.input)

        m.d.comb += self.core_input.connect_upstream(tee.get_output(), allow_partial=True)

        metadata_fifo_input = Stream()
        for name, s in self.input.out_of_band_signals.items():
            setattr(metadata_fifo_input, name, Signal.like(s) @ DOWNWARDS)
        m.d.comb += metadata_fifo_input.connect_upstream(tee.get_output(), allow_partial=True)
        metadata_fifo = m.submodules.metadata_fifo = BufferedSyncStreamFIFO(metadata_fifo_input, self.fifo_depth)

        combiner = m.submodules.combiner = StreamCombiner(self.core_output, metadata_fifo.output)
        m.d.comb += self.output.connect_upstream(combiner.output)

        return m
