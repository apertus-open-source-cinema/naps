from nmigen import *
from nmigen.vendor.lattice_machxo_2_3l import LatticeMachXO2Platform
from nmigen.vendor.xilinx_7series import Xilinx7SeriesPlatform


class JTAG(Elaboratable):
    def __init__(self):
        self.shift_read = Signal()
        self.shift_write = Signal()
        self.tdi = Signal()
        self.tdo = Signal()
        self.reset = Signal()
        self.update = Signal()

    def elaborate(self, platform):
        m = Module()

        if isinstance(platform, Xilinx7SeriesPlatform):
            # we delay tdi and shift by one cycle to match the behaviour of the lattice jtag primitives
            tck = Signal()
            shift = Signal()
            m.submodules.inst = Instance(
                "BSCANE2",
                p_JTAG_CHAIN=1,

                o_TCK=tck,
                o_TDI=self.tdi,
                o_SHIFT=shift,
                o_RESET=self.reset,

                i_TDO=self.tdo,
            )

            m.d.comb += self.shift_read.eq(shift)
            m.d.comb += self.shift_write.eq(shift)
            m.domains += ClockDomain("jtag")
            m.d.comb += ClockSignal("jtag").eq(tck)
        elif isinstance(platform, LatticeMachXO2Platform):
            # the lattice jtag primitive is rather wired and has a one cycle delay on tdi
            # we hack around this in the jtag state machine
            jce1 = Signal()
            jrti1 = Signal()
            jshift = Signal()
            jtck = Signal(attrs={"KEEP": "TRUE"})
            jrstn = Signal()

            platform.add_clock_constraint(jtck, 1e6)
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

            m.d.comb += self.shift_write.eq(jshift)
            # we delay the shift signal for read by one clock cycle because tdi is also delayed by one clock cycle
            m.domains += ClockDomain("jtagn")
            m.d.comb += ClockSignal("jtagn").eq(jtck)
            m.d.jtagn += self.shift_read.eq(jshift)

            # we must sample tdi on the negedge
            m.domains += ClockDomain("jtag")
            m.d.comb += ClockSignal("jtag").eq(~jtck)

        return m
