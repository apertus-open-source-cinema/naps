from nmigen import *
from nmigen.vendor.lattice_machxo_2_3l import LatticeMachXO2Platform
from nmigen.vendor.xilinx_7series import Xilinx7SeriesPlatform


class JTAG(Elaboratable):
    def __init__(self):
        self.tck = Signal()
        self.shift = Signal()
        self.tdi = Signal()
        self.tdo = Signal()
        self.reset = Signal()
        self.update = Signal()

    def elaborate(self, platform):
        m = Module()

        m.domains += ClockDomain("jtag")
        m.d.comb += ClockSignal("jtag").eq(self.tck)

        if isinstance(platform, Xilinx7SeriesPlatform):
            # we delay tdi and shift by one cycle to match the behaviour of the lattice jtag primitives
            m.submodules.inst = Instance(
                "BSCANE2",
                p_JTAG_CHAIN=1,

                o_TCK=self.tck,
                o_TDI=self.tdi,
                o_SHIFT=self.shift,
                o_RESET=self.reset,

                i_TDO=self.tdo,
            )
        elif isinstance(platform, LatticeMachXO2Platform):
            # the lattice jtag primitive is rather wired and has a one cycle delay on tdi
            # we hack around this in the jtag state machine
            jce1 = Signal()
            jrti1 = Signal()
            jshift = Signal()
            jtck = Signal()
            jrstn = Signal()
            m.submodules += Instance(
                "JTAGF",
                i_JTDO1=self.tdo,
                o_JTDI=self.tdi,
                o_JTCK=jtck,
                o_JRTI1=jrti1,
                o_JRSTN=jrstn,
                o_JSHIFT=jshift,
                o_JCE1=jce1,
                o_JUPDATE=self.update,
            )
            m.d.comb += self.reset.eq(~jrstn)
            m.d.jtag += self.shift.eq(jshift)
            m.d.comb += self.tck.eq(~jtck)

            m.d.comb += platform.jtag_signals.eq(Cat(self.tdi, self.tdo, jtck, jshift, jrti1, jce1, jrstn, self.update))

        return m
