from nmigen import *

from xilinx.clocking import RawPll, Bufg
from xilinx.io import Iserdes

class HispiPhy(Elaboratable):
    def __init__(self, num_lanes=4):
        self.hispi_clk = Signal()
        self.hispi_lanes = Signal(num_lanes)

        self.dout = [Signal(6)] * num_lanes

    def elaborate(self, platform):
        m = Module()

        pll = m.submodules.pll = RawPll(startup_wait=False, ref_jitter1=0.01, clkin1_period=3.333,
                                        clkfbout_mult=3, divclk_divide=1,
                                        clkout0_divide=9, clkout0_phase=0.0,
                                        clkout1_divide=3, clkout1_phase=0.0,
                                        clkout2_divide=18, clkout2_phase=0.0)
        m.d.comb += pll.clk.in_[1].eq(self.hispi_clk)
        m.d.comb += pll.clk.fbin.eq(pll.clk.fbout)

        bufg_hispi = m.submodules.bufg_hispi = Bufg(pll.clk.out[1])
        m.domains += ClockDomain("hispi")
        m.d.comb += ClockSignal("hispi").eq(bufg_hispi.o)

        bufg_hispi_half_word = m.submodules.bufg_hispi_half_word = Bufg(pll.clk.out[0])
        m.domains += ClockDomain("hispi_half_word")
        m.d.comb += ClockSignal("hispi_half_word").eq(bufg_hispi_half_word.o)

        bufg_hispi_word = m.submodules.bufg_hispi_word = Bufg(pll.clk.out[2])
        m.domains += ClockDomain("hispi_word")
        m.d.comb += ClockSignal("hispi_word").eq(bufg_hispi_word.o)

        for i in range(0, len(self.hispi_lanes)):
            iserdes = m.submodules["hispi_iserdes_" + str(i)] = Iserdes(
                data_width=6,
                data_rate="ddr",
                serdes_mode="master",
                interface_type="networking",
                num_ce=1,
                iobDelay="none",
            )

            m.d.comb += iserdes.d.eq(self.hispi_lanes[i])
            m.d.comb += iserdes.ce[1].eq(1)
            m.d.comb += iserdes.clk.eq(ClockSignal("hispi"))
            m.d.comb += iserdes.clkb.eq(~ClockSignal("hispi"))
            m.d.comb += iserdes.rst.eq(ResetSignal("hispi"))
            m.d.comb += iserdes.clkdiv.eq(ClockSignal("hispi_half_word"))

            m.d.comb += self.dout[i].eq(Cat(iserdes.q[j] for j in range(1, 7)))

        return m
