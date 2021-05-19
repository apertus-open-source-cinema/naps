from nmigen import *
from ..generic.jtag import JTAG as GenericJTAG


class JTAG(GenericJTAG.implementation):
    # the lattice jtag primitive is rather wired and has a one cycle delay on tdi

    def elaborate(self, platform):
        m = Module()

        cd = ClockDomain(self.jtag_domain)
        m.domains += cd
        clock_signal = Signal()
        m.d.comb += cd.clk.eq(~clock_signal)  # we do this to avoid using a negedge clockdomain (see: https://github.com/nmigen/nmigen/issues/611)
        platform.add_clock_constraint(clock_signal, 1e6)

        shift = Signal()  # for some reason we also have to delay shift
        m.d.comb += self.shift_tdo.eq(shift)
        m.d.jtag += self.shift_tdi.eq(shift)

        m.submodules.jtag_primitive = Instance(
            "JTAGG",
            i_JTDO1=self.tdo,
            o_JTDI=self.tdi,
            o_JTCK=clock_signal,
            o_JSHIFT=shift,
        )

        return m