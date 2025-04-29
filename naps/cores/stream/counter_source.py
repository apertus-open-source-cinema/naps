from amaranth import *
from amaranth.lib import wiring, stream
from amaranth.lib.wiring import Out, Component
from naps import ControlSignal

__all__ = ["CounterStreamSource"]


class CounterStreamSource(Component):
    def __init__(self, width, count_if_not_ready=False):
        super().__init__(wiring.Signature({
            "output": Out(stream.Signature(width))
        }))

        self.count_if_not_ready = ControlSignal(init=count_if_not_ready)

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.output.valid.eq(1)
        with m.If(self.output.ready | self.count_if_not_ready):
            m.d.sync += self.output.payload.eq(self.output.payload + 1)

        return m
