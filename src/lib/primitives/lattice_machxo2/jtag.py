from nmigen import *

from lib.primitives.generic.jtag import JTAG as GenericJTAG


class JTAG(GenericJTAG.implementation):
    # the lattice jtag primitive is rather wired and has a one cycle delay on tdi

    def elaborate(self, platform):
        m = Module()

        print("warning: lattice JTAGF primitive is buggy as fuck")

        jtck = Signal(attrs={"KEEP": "TRUE"})
        platform.add_clock_constraint(jtck, 1e6)
        m.domains += ClockDomain("jtag", clk_edge="neg")  # we must sample tdo at the falling edge for some reason
        m.d.comb += ClockSignal("jtag").eq(jtck)

        shift = Signal()  # for some reason we also have to delay shift
        m.d.comb += self.shift_tdo.eq(shift)
        m.d.jtag += self.shift_tdi.eq(shift)

        m.submodules.jtag_primitive = Instance(
            "JTAGF",
            i_JTDO1=self.tdo,
            o_JTDI=self.tdi,
            o_JTCK=jtck,
            o_JSHIFT=shift,
        )

        return m
