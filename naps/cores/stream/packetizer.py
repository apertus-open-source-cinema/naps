from amaranth import *
from naps.data_structure import DOWNWARDS
from naps.soc.csr_types import PulseReg
from naps.stream import BasicStream

__all__ = ["StreamPacketizer"]


class StreamPacketizer(Elaboratable):
    """Converts a BasicStream into a Packetized Stream with a new packet being startable via a register"""
    def __init__(self, input: BasicStream):
        self.input = input
        self.output = input.clone()
        self.output.last = Signal() @ DOWNWARDS

        self.new_packet = PulseReg(1)

    def elaborate(self, platform):
        m = Module()

        m.submodules += self.new_packet
        m.d.comb += self.output.connect_upstream(self.input, exclude=["last"])
        m.d.comb += self.output.last.eq(self.new_packet.pulse)

        return m
