from nmigen import *

from cores.csr_bank import StatusSignal
from xilinx.clocking import Mmcm
from xilinx.io import Iserdes


class HispiPhy(Elaboratable):
    def __init__(self, num_lanes=4, bits=12):
        assert bits == 12

        self.hispi_clk = Signal()
        self.hispi_lanes = Signal(num_lanes)

        self.bitslip = [Signal() for _ in range(num_lanes)]
        self.out = [Signal(12) for _ in range(num_lanes)]

        self.hispi_x6_in_domain_counter = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        m.domains += ClockDomain("hispi_x6_in")
        m.d.comb += ClockSignal("hispi_x6_in").eq(self.hispi_clk)
        m.d.hispi_x6_in += self.hispi_x6_in_domain_counter.eq(self.hispi_x6_in_domain_counter + 1)

        mul = 3
        pll = m.submodules.pll = Mmcm(300e6, mul, 1, input_domain="hispi_x6_in")
        pll.output_domain("hispi_x6", mul * 1)
        pll.output_domain("hispi_x3", mul * 2)
        pll.output_domain("hispi_x2", mul * 3)
        pll.output_domain("hispi", mul * 6)

        for i in range(0, len(self.hispi_lanes)):
            iserdes = m.submodules["hispi_iserdes_" + str(i)] = Iserdes(
                data_width=6,
                data_rate="ddr",
                serdes_mode="master",
                interface_type="networking",
                num_ce=1,
                iobDelay="none",
            )

            m.d.comb += iserdes.bitslip.eq(self.bitslip[i])
            m.d.comb += iserdes.d.eq(self.hispi_lanes[i])
            m.d.comb += iserdes.ce[1].eq(1)
            m.d.comb += iserdes.clk.eq(ClockSignal("hispi_x6"))
            m.d.comb += iserdes.clkb.eq(~ClockSignal("hispi_x6"))
            m.d.comb += iserdes.rst.eq(ResetSignal("hispi_x6"))
            m.d.comb += iserdes.clkdiv.eq(ClockSignal("hispi_x2"))

            iserdes_output = Cat(iserdes.q[j] for j in reversed(range(1, 7)))
            with m.FSM(domain="hispi_x2"):
                with m.State("lower"):
                    m.d.hispi_x2 += self.out[i][0:6].eq(iserdes_output)
                    m.next = "upper"
                with m.State("upper"):
                    m.d.hispi_x2 += self.out[i][6:12].eq(iserdes_output)
                    m.next = "lower"

        return m
