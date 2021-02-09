from nmigen import *

from lib.bus.stream.stream import BasicStream
from lib.bus.stream.stream_transformer import stream_transformer


class StreamBuffer(Elaboratable):
    """Basically a 1 deep Stream FIFO. Can be used to improve timing or to make outputs compliant with the Stream contract"""
    def __init__(self, input: BasicStream):
        self.input = input
        self.output = input.clone()

    def elaborate(self, platform):
        m = Module()

        stream_transformer(self.input, self.output, m, latency=1)
        with m.If(self.input.ready & self.input.valid):
            m.d.sync += self.output.connect_upstream(self.input, exclude=["ready", "valid"])

        return m
