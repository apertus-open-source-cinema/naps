from nmigen import *
from nmigen.lib.cdc import FFSynchronizer

from naps import StatusSignal, ControlSignal, iterator_with_if_elif
from naps.vendor.xilinx_s7 import Mmcm
from naps.vendor.xilinx_s7.io import _ISerdes


class HispiPhy(Elaboratable):
    def __init__(self, num_lanes=4, bits=12, hispi_domain="hispi"):
        assert bits == 12
        self.hispi_domain = hispi_domain

        self.hispi_clk = Signal()
        self.hispi_lanes = Signal(num_lanes)

        self.bitslip = [Signal() for _ in range(num_lanes)]
        self.out = [Signal(12) for _ in range(num_lanes)]

        self.hispi_x6_in_domain_counter = StatusSignal(32)
        self.enable_bitslip = ControlSignal(reset=1)
        self.word_reverse = ControlSignal()

    def elaborate(self, platform):
        m = Module()

        hispi_6_in = "{}_x6_in".format(self.hispi_domain)
        m.domains += ClockDomain(hispi_6_in)
        m.d.comb += ClockSignal(hispi_6_in).eq(self.hispi_clk)
        m.d[hispi_6_in] += self.hispi_x6_in_domain_counter.eq(self.hispi_x6_in_domain_counter + 1)

        mul = 3
        pll = m.submodules.pll = Mmcm(300e6, mul, 1, input_domain=hispi_6_in.format(self.hispi_domain))
        pll.output_domain("{}_x6".format(self.hispi_domain), mul * 1)
        pll.output_domain("{}_x3".format(self.hispi_domain), mul * 2)
        pll.output_domain("{}_x2".format(self.hispi_domain), mul * 3)
        pll.output_domain("{}".format(self.hispi_domain), mul * 6)

        for lane in range(0, len(self.hispi_lanes)):
            iserdes = m.submodules["hispi_iserdes_" + str(lane)] = _ISerdes(
                data_width=6,
                data_rate="DDR",
                serdes_mode="master",
                interface_type="networking",
                num_ce=1,
                iobDelay="none",
            )

            m.d.comb += iserdes.d.eq(self.hispi_lanes[lane])
            m.d.comb += iserdes.ce[1].eq(1)
            m.d.comb += iserdes.clk.eq(ClockSignal("{}_x6".format(self.hispi_domain)))
            m.d.comb += iserdes.clkb.eq(~ClockSignal("{}_x6".format(self.hispi_domain)))
            m.d.comb += iserdes.rst.eq(ResetSignal("{}_x6".format(self.hispi_domain)))
            m.d.comb += iserdes.clkdiv.eq(ClockSignal("{}_x2".format(self.hispi_domain)))

            data = Signal(12)
            iserdes_output = Signal(6)
            m.d.comb += iserdes_output.eq(Cat(iserdes.q[j] for j in range(1, 7)))

            hispi_x2 = "{}_x2".format(self.hispi_domain)
            lower_upper_half = Signal()
            m.d[hispi_x2] += lower_upper_half.eq(~lower_upper_half)
            with m.If(lower_upper_half):
                m.d[hispi_x2] += data[6:12].eq(iserdes_output)
            with m.Else():
                m.d[hispi_x2] += data[0:6].eq(iserdes_output)

            data_in_hispi_domain = Signal(12)
            m.submodules["data_cdc_{}".format(lane)] = FFSynchronizer(data, data_in_hispi_domain, o_domain=self.hispi_domain)

            hispi_domain = m.d[self.hispi_domain]
            bitslip = Signal()
            was_bitslip = Signal()
            hispi_domain += was_bitslip.eq(bitslip)
            with m.If(self.bitslip[lane] & ~was_bitslip & self.enable_bitslip):
                hispi_domain += bitslip.eq(1)
            with m.Else():
                hispi_domain += bitslip.eq(0)

            serdes_or_emulated_bitslip = Signal()
            with m.If(bitslip):
                hispi_domain += serdes_or_emulated_bitslip.eq(~serdes_or_emulated_bitslip)

            m.d.comb += iserdes.bitslip.eq(bitslip & serdes_or_emulated_bitslip)

            data_order_index = Signal(range(4))
            with m.If(bitslip & ~serdes_or_emulated_bitslip):
                hispi_domain += data_order_index.eq(data_order_index + 1)

            data_order = StatusSignal(range(16))
            setattr(self, "data_order_{}".format(lane), data_order)
            m.d.comb += data_order.eq(Array((1, 4, 9, 12))[data_order_index])

            current = Signal(12)
            last = Signal(12)
            m.d.comb += current.eq(data_in_hispi_domain)
            hispi_domain += last.eq(data_in_hispi_domain)
            reordered = Signal(12)
            parts = [current[0:6], current[6:12], last[0:6], last[6:12]]
            for cond, i in iterator_with_if_elif(range(16), m):
                with cond(data_order == i):
                    first = parts[i % 4]
                    second = parts[i // 4]
                    m.d.comb += reordered.eq(Cat(first, second))

            with m.If(self.word_reverse):
                m.d.comb += self.out[lane].eq(Cat(reordered[i] for i in range(12)))
            with m.Else():
                m.d.comb += self.out[lane].eq(Cat(reordered[i] for i in reversed(range(12))))

            out_status_signal = StatusSignal(12, name="out_{}".format(lane))
            setattr(self, "out_{}".format(lane), out_status_signal)
            m.d.comb += out_status_signal.eq(data_in_hispi_domain)

        return m
