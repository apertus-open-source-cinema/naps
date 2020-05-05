from itertools import product

from nmigen import *
from nmigen.build import Clock

from modules.vendor.litevideo_hdmi.s7 import S7HDMIOutPHY
from modules.xilinx.Ps7 import Ps7
from modules.xilinx.clocking import Mmcm
from util.cvt import calculate_video_timing
from util.nmigen import max_error_freq


class Hdmi(Elaboratable):
    def __init__(self, width, height, refresh, pins):
        self.pins = pins
        self.width, self.height, self.refresh = width, height, refresh
        self.pix_freq = Clock(calculate_video_timing(width, height, refresh)["pxclk"] * 1e6)

        self.timing_generator: TimingGenerator = DomainRenamer("pix")(
            TimingGenerator(self.width, self.height, self.refresh)
        )
        self.pattern_generator: XorPatternGenerator = DomainRenamer("pix")(
            XorPatternGenerator(self.width, self.height)
        )

        valid_configs = (
            (abs(1 - ((fclk * mul / div) / (self.pix_freq.frequency * 5 * output_div))),
             fclk, mul, div, output_div)
            for fclk, mul, div, output_div in product(Ps7.get_possible_fclk_frequencies(), Mmcm.vco_multipliers, [1], [1, 2])
            if Mmcm.is_valid_vco_conf(fclk, mul, div)
        )
        deviation, self.fclk_freq, mmcm_mul, mmcm_div, self.output_div = sorted(valid_configs)[0]
        print("pixclk error: {}%. (fclk={}MHz; mul={}; div={}; output_div={})".format(deviation, self.fclk_freq / 1e6, mmcm_mul, mmcm_div, self.output_div))
        self.mmcm: Mmcm = Mmcm(
            input_clock=self.fclk_freq, input_domain="pix_synth_fclk",
            vco_mul=mmcm_mul, vco_div=mmcm_div
        )

    def elaborate(self, platform):
        m = Module()

        platform.get_ps7().fck_domain(self.fclk_freq, "pix_synth_fclk")
        mmcm = m.submodules.mmcm = self.mmcm
        actual_pix_freq = mmcm.output_domain("pix", 5 * self.output_div)
        error_percent = max_error_freq(actual_pix_freq.frequency, self.pix_freq.frequency)

        # the signal is to fast for a bufg; TODO: seems like it instanciates one no matter of that parameter
        mmcm.output_domain("pix5x", self.output_div, bufg=False)

        m.submodules.timing_generator = self.timing_generator
        m.submodules.pattern_generator = self.pattern_generator

        m.d.comb += [
            self.pattern_generator.x.eq(self.timing_generator.x),
            self.pattern_generator.y.eq(self.timing_generator.y)
        ]

        phy = m.submodules.phy = S7HDMIOutPHY()
        m.d.comb += [
            phy.hsync.eq(self.timing_generator.hsync),
            phy.vsync.eq(self.timing_generator.vsync),
            phy.data_enable.eq(self.timing_generator.active),

            phy.r.eq(self.pattern_generator.out.r),
            phy.g.eq(self.pattern_generator.out.g),
            phy.b.eq(self.pattern_generator.out.b),

            self.pins.data.eq(phy.outputs)
        ]

        return m


class TimingGenerator(Elaboratable):
    def __init__(self, width, height, refresh):
        self.video_timing = calculate_video_timing(width, height, refresh)

        self.x = Signal(range(self.video_timing["hscan"] + 1))
        self.y = Signal(range(self.video_timing["vscan"] + 1))
        self.active = Signal()
        self.hsync = Signal()
        self.vsync = Signal()

    def elaborate(self, plat):
        m = Module()

        # set the xy coordinates
        with m.If(self.x < self.video_timing["hscan"]):
            m.d.sync += self.x.eq(self.x + 1)
        with m.Else():
            m.d.sync += self.x.eq(0)
            with m.If(self.y < self.video_timing["vscan"]):
                m.d.sync += self.x.eq(self.y + 1)
            with m.Else():
                m.d.sync += self.y.eq(0)

        m.d.comb += [
            self.active.eq((self.x < self.video_timing["hres"]) & (self.y < self.video_timing["vres"])),
            self.hsync.eq((self.x > self.video_timing["hsync_start"]) & (self.x <= self.video_timing["hsync_end"])),
            self.vsync.eq((self.y > self.video_timing["vsync_start"]) & (self.x <= self.video_timing["vsync_end"]))
        ]

        return m


class XorPatternGenerator(Elaboratable):
    def __init__(self, width, height):
        self.x = Signal(range(width))
        self.y = Signal(range(height))
        self.out = Record((
            ("r", 8),
            ("g", 8),
            ("b", 8)
        ))

    def elaborate(self, plat):
        m = Module()

        m.d.comb += [
            self.out.r.eq(self.x ^ self.y),
            self.out.g.eq((self.x + 1) ^ self.y),
            self.out.b.eq(self.x ^ (self.y + 1))
        ]

        return m
