from amaranth import *
from naps import BasicStream, ControlSignal

__all__ = ["CounterStreamSource"]


class CounterStreamSource(Elaboratable):
    def __init__(self, width, count_if_not_ready=False):
        self.output = BasicStream(width, name="counter_stream")

        self.count_if_not_ready = ControlSignal(init=count_if_not_ready)

    def elaborate(self, platform):
        m = Module()

        # we initialize our counter with one to compensate for the 2 cycle delay
        # from it to the payload
        counter = Signal(self.output.payload.shape(), init=1)

        m.d.comb += self.output.valid.eq(1)
        with m.If(self.output.ready | self.count_if_not_ready):
            m.d.sync += counter.eq(counter + 1)

        with m.If(self.output.ready):
            m.d.sync += self.output.payload.eq(counter)

        return m
