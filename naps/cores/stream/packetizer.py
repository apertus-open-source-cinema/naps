from amaranth import *
from naps.data_structure import DOWNWARDS
from naps.soc.csr_types import PulseReg, ControlSignal
from naps.stream import BasicStream

__all__ = ["StreamPacketizer"]


class StreamPacketizer(Elaboratable):
    """Converts a BasicStream into a Packetized Stream with a new packet being startable via a register"""
    def __init__(self, input: BasicStream):
        self.input = input
        self.output = input.clone()
        self.output.last = Signal() @ DOWNWARDS

        self.length = ControlSignal(32)
        self.start = PulseReg(1)

    def elaborate(self, platform):
        m = Module()

        m.submodules += self.start

        counter = Signal(32)
        with m.If((counter > 0) & (counter <= self.length) & self.output.ready & self.input.valid):
            m.d.sync += counter.eq(counter + 1)
            m.d.comb += self.output.last.eq(counter == self.length - 1)
            m.d.comb += self.output.connect_upstream(self.input, exclude=["last"])
        with m.If(self.start.pulse):
            m.d.sync += counter.eq(1)

        return m
