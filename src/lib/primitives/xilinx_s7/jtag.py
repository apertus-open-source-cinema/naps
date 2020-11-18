from nmigen import *

from lib.primitives.generic.jtag import JTAG as GenericJTAG


class JTAG(GenericJTAG.implementation):
    def elaborate(self, platform):
        m = Module()
        tck = Signal(attrs={"KEEP": "TRUE"})
        platform.add_clock_constraint(tck, 1e6)
        m.domains += ClockDomain("jtag")
        m.d.comb += ClockSignal("jtag").eq(tck)

        m.submodules.jtag_primitive = Instance(
            "BSCANE2",
            p_JTAG_CHAIN=1,

            o_TCK=tck,
            o_TDI=self.tdi,
            o_SHIFT=self.shift,

            i_TDO=self.tdo,
        )
        return m
