from nmigen import *
from nmigen.vendor.lattice_machxo_2_3l import LatticeMachXO2Platform
from nmigen.vendor.xilinx_7series import Xilinx7SeriesPlatform


class JTAG(Elaboratable):
    def __init__(self):
        self.shift = Signal()
        self.tdi = Signal()
        self.tdo = Signal()

    def elaborate(self, platform):
        m = Module()

        if isinstance(platform, Xilinx7SeriesPlatform):
            # we delay tdi and shift by one cycle to match the behaviour of the lattice jtag primitives
            tck = Signal()
            m.submodules.jtag_primitive = Instance(
                "BSCANE2",
                p_JTAG_CHAIN=1,

                o_TCK=tck,
                o_TDI=self.tdi,
                o_SHIFT=self.shift,

                i_TDO=self.tdo,
            )
            m.domains += ClockDomain("jtag")
            m.d.comb += ClockSignal("jtag").eq(tck)

        elif isinstance(platform, LatticeMachXO2Platform):
            print("using lattice MACHXO2 JTAG primitive")
            # the lattice jtag primitive is rather wired and has a one cycle delay on tdi
            # we hack around this in the jtag state machine
            jshift = Signal()
            jtck = Signal(attrs={"KEEP": "TRUE"})

            platform.add_clock_constraint(jtck, 1e6)
            m.submodules.jtag_primitive = Instance(
                "JTAGF",
                i_JTDO1=self.tdo,
                o_JTDI=self.tdi,
                o_JTCK=jtck,
                o_JSHIFT=jshift,
                o_JUPDATE=self.update,
            )

            # we delay the shift signal for by one clock cycle because tdi is also delayed by one clock cycle
            m.domains += ClockDomain("jtagn")
            m.d.comb += ClockSignal("jtagn").eq(jtck)
            m.d.jtagn += self.shift.eq(jshift)

            # we must sample tdi on the negedge
            m.domains += ClockDomain("jtag")
            m.d.comb += ClockSignal("jtag").eq(~jtck)

        return m
