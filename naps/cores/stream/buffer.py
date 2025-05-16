from amaranth import *
from amaranth import ShapeLike
from amaranth.lib import stream, wiring
from amaranth.lib.wiring import Component, In, Out

__all__ = ["StreamBuffer"]

from naps import real_payload
from naps.stream.stream_transformer import stream_transformer


class StreamBuffer(Component):
    """Basically a 1 deep Stream FIFO. Can be used to improve timing or to make outputs compliant with the Stream contract"""
    def __init__(self, shape: ShapeLike):
        super().__init__(wiring.Signature({
            "input": In(stream.Signature(shape)),
            "output": Out(stream.Signature(shape)),
        }))

    def elaborate(self, platform):
        m = Module()

        input_transaction = stream_transformer(m, self.input, self.output, latency=1)
        with m.If(input_transaction):
            m.d.sync += real_payload(self.output.p).eq(real_payload(self.input.payload))

        return m
