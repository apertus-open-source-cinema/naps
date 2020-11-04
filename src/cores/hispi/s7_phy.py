from nmigen import *
from nmigen.hdl.ast import Rose

from cores.csr_bank import StatusSignal
from cores.primitives.xilinx_s7.clocking import Mmcm
from cores.primitives.xilinx_s7.io import Iserdes
from nmigen.lib.cdc import FFSynchronizer


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
                data_rate="DDR",
                serdes_mode="master",
                interface_type="networking",
                num_ce=1,
                iobDelay="none",
            )

            m.d.comb += iserdes.d.eq(self.hispi_lanes[i])
            m.d.comb += iserdes.ce[1].eq(1)
            m.d.comb += iserdes.clk.eq(ClockSignal("hispi_x6"))
            m.d.comb += iserdes.clkb.eq(~ClockSignal("hispi_x6"))
            m.d.comb += iserdes.rst.eq(ResetSignal("hispi_x6"))
            m.d.comb += iserdes.clkdiv.eq(ClockSignal("hispi_x2"))

            data = Signal(12)
            iserdes_output = Cat(iserdes.q[j] for j in range(1, 7))
            lower_upper_half = Signal()
            m.d.hispi_x2 += lower_upper_half.eq(~lower_upper_half)
            with m.If(lower_upper_half):
                m.d.hispi_x2 += data[6:12].eq(iserdes_output)
            with m.Else():
                m.d.hispi_x2 += data[0:6].eq(iserdes_output)

            data_in_hispi_domain = Signal(12)
            m.submodules["data_cdc_{}".format(i)] = FFSynchronizer(data, data_in_hispi_domain, o_domain="hispi")

            bitslip = Signal()
            was_bitslip = Signal()
            m.d.hispi += was_bitslip.eq(bitslip)
            with m.If(self.bitslip[i] & ~was_bitslip):
                m.d.hispi += bitslip.eq(1)
            with m.Else():
                m.d.hispi += bitslip.eq(0)

            iserdes_or_emulated_bitslip = Signal()
            with m.If(bitslip):
                m.d.hispi += iserdes_or_emulated_bitslip.eq(~iserdes_or_emulated_bitslip)

            m.d.comb += iserdes.bitslip.eq(bitslip & iserdes_or_emulated_bitslip)

            order = Signal()
            with m.If(bitslip & ~iserdes_or_emulated_bitslip):
                m.d.hispi += order.eq(~order)

            with m.If(order):
                m.d.hispi += self.out[i].eq(Cat(data_in_hispi_domain[0:6], data_in_hispi_domain[6:12]))
            with m.Else():
                m.d.hispi += self.out[i].eq(Cat(data_in_hispi_domain[6:12], data_in_hispi_domain[0:6]))
            out_status_signal = StatusSignal(12, name="out_{}".format(i))
            setattr(self, "out_{}".format(i), out_status_signal)
            m.d.comb += out_status_signal.eq(data_in_hispi_domain)

        return m
