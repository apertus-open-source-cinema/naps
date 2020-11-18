from nmigen import *

from lib.primitives.generic.jtag import JTAG as GenericJTAG


class JTAG(GenericJTAG.implementation):
    # the lattice jtag primitive is rather wired and has a one cycle delay on tdi

    def elaborate(self, platform):
        m = Module()

        jtck = Signal(attrs={"KEEP": "TRUE"})
        platform.add_clock_constraint(jtck, 1e6)
        m.domains += ClockDomain("jtag")
        m.d.comb += ClockSignal("jtag").eq(jtck)

        m.submodules.jtag_primitive = Instance(
            "JTAGF",
            i_JTDO1=self.tdo,
            o_JTDI=self.tdi,
            o_JTCK=jtck,
            o_JSHIFT=self.shift,
        )
        return m
