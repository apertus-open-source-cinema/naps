from nmigen import *

from util.stream import StreamEndpoint


class CounterStreamSource(Elaboratable):
    def __init__(self, width):
        self.output = StreamEndpoint(width, is_sink=False, has_last=False)

    def elaborate(self, platform):
        m = Module()

        with m.If(self.output.ready):
            m.d.comb += self.output.valid.eq(1)
            m.d.sync += self.output.payload.eq(self.output.payload + 1)

        return m
