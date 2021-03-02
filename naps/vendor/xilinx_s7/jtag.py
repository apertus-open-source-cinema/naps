from nmigen import *

from naps.vendor import JTAG as GenericJTAG


class JTAG(GenericJTAG.implementation):
    def elaborate(self, platform):
        m = Module()
        tck = Signal(attrs={"KEEP": "TRUE"})
        platform.add_clock_constraint(tck, 1e6)
        m.domains += ClockDomain(self.jtag_domain)
        m.d.comb += ClockSignal(self.jtag_domain).eq(tck)

        shift = Signal()
        m.d.comb += self.shift_tdi.eq(shift)
        m.d.comb += self.shift_tdo.eq(shift)

        m.submodules.jtag_primitive = Instance(
            "BSCANE2",
            p_JTAG_CHAIN=1,

            o_TCK=tck,
            o_TDI=self.tdi,
            o_SHIFT=shift,

            i_TDO=self.tdo,
        )
        return m
