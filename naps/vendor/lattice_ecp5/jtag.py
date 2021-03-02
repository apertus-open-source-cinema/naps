from nmigen import *
from ..generic.jtag import JTAG as GenericJTAG


class JTAG(GenericJTAG.implementation):
    # the lattice jtag primitive is rather wired and has a one cycle delay on tdi

    def elaborate(self, platform):
        m = Module()

        cd = ClockDomain(self.jtag_domain, clk_edge="neg")  # we must sample tdo at the falling edge for some reason
        m.domains += cd
        platform.add_clock_constraint(cd.clk, 1e6)

        shift = Signal()  # for some reason we also have to delay shift
        m.d.comb += self.shift_tdo.eq(shift)
        m.d.jtag += self.shift_tdi.eq(shift)

        m.submodules.jtag_primitive = Instance(
            "JTAGG",
            i_JTDO1=self.tdo,
            o_JTDI=self.tdi,
            o_JTCK=cd.clk,
            o_JSHIFT=shift,
        )

        return m