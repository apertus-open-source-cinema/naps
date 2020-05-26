from itertools import product

from nmigen import *
from nmigen.build import Clock

from util.bundle import Bundle
from soc.reg_types import StatusSignal, ControlSignal
from modules.hdmi.s7 import HDMIOutPHY
from modules.xilinx.Ps7 import Ps7
from modules.xilinx.clocking import Mmcm
from util.cvt import parse_modeline
from util.nmigen import max_error_freq


class Hdmi(Elaboratable):
    def __init__(self, plugin, modeline, generate_clocks=True):
        self.plugin = plugin
        self.generate_clocks = generate_clocks
        video_timing = parse_modeline(modeline)
        self.pix_freq = Clock(video_timing.pxclk * 1e6)

        self.hsync_polarity = ControlSignal()
        self.vsync_polarity = ControlSignal()

        self.timing_generator: TimingGenerator = DomainRenamer("pix")(
            TimingGenerator(video_timing)
        )
        self.pattern_generator: BertlPatternGenerator = DomainRenamer("pix")(
            BertlPatternGenerator(self.timing_generator.width, self.timing_generator.height)
        )

    def elaborate(self, platform):
        m = Module()

        if self.generate_clocks:
            m.submodules.clocking = HdmiClocking(self.pix_freq)
        m.submodules.timing_generator = self.timing_generator
        m.submodules.pattern_generator = self.pattern_generator

        m.d.comb += [
            self.pattern_generator.x.eq(self.timing_generator.x),
            self.pattern_generator.y.eq(self.timing_generator.y)
        ]

        phy = m.submodules.phy = HDMIOutPHY()
        m.d.pix += [
            phy.hsync.eq(self.timing_generator.hsync ^ self.hsync_polarity),
            phy.vsync.eq(self.timing_generator.vsync ^ self.vsync_polarity),
            phy.data_enable.eq(self.timing_generator.active),

            phy.r.eq(self.pattern_generator.out.r),
            phy.g.eq(self.pattern_generator.out.g),
            phy.b.eq(self.pattern_generator.out.b),
        ]

        m.d.comb += [
            self.plugin.data.eq(phy.outputs),
            self.plugin.clock.eq(phy.clock)
        ]

        m.submodules.plugin = PluginLowspeedController(self.plugin)

        return m


class PluginLowspeedController(Elaboratable):
    def __init__(self, plugin):
        self.plugin = plugin

    def elaborate(self, platform):
        m = Module()

        # generate low speed CSR signals
        if hasattr(self.plugin, "output_enable"):
            for name, signal_type, width, default in [
                ("output_enable", ControlSignal, 1, 1),
                ("equalizer", ControlSignal, 2, 0b11),
                ("dcc_enable", ControlSignal, 1, 0),
                ("vcc_enable", ControlSignal, 1, 1),
                ("ddet", ControlSignal, 1, 0),
                ("ihp", StatusSignal, 1, 0),
            ]:
                csr_signal = signal_type(width, reset=default)
                setattr(self, name, csr_signal)
                io = getattr(self.plugin, name)
                if signal_type == ControlSignal:
                    m.d.comb += io.eq(csr_signal)
                else:
                    m.d.comb += csr_signal.eq(io)

        return m


class HdmiClocking(Elaboratable):
    def __init__(self, pix_freq):
        self.pix_freq = pix_freq

    def find_valid_config(self):
        # fast path:
        for output_div in range(1, 6):
            for fclk_frequency in [10e6, 20e6]:
                for mmcm_mul in reversed(Mmcm.vco_multipliers):
                    if (fclk_frequency * mmcm_mul / output_div) == self.pix_freq.frequency * 5:
                        self.mmcm_mul = mmcm_mul
                        self.fclk_freq = fclk_frequency
                        self.output_div = output_div
                        self.mmcm_div = 1
                        return

        # always working path:
        valid_configs = (
            (abs(1 - ((fclk * mul / div) / (self.pix_freq.frequency * 5 * output_div))),
             fclk, mul, div, output_div)
            for fclk, mul, div, output_div in
            product([f for f in Ps7.get_possible_fclk_frequencies() if 1e6 <= f <= 100e6], Mmcm.vco_multipliers, [1],
                    range(1, 6))
            if Mmcm.is_valid_vco_conf(fclk, mul, div)
        )
        deviation, self.fclk_freq, self.mmcm_mul, self.mmcm_div, self.output_div = sorted(valid_configs)[0]

    def elaborate(self, platform):
        m = Module()

        self.find_valid_config()
        platform.get_ps7().fck_domain(self.fclk_freq, "pix_synth_fclk")
        mmcm = m.submodules.mmcm = Mmcm(
            input_clock=self.fclk_freq, input_domain="pix_synth_fclk",
            vco_mul=self.mmcm_mul, vco_div=self.mmcm_div
        )

        deviation = (abs(
            1 - ((self.fclk_freq * self.mmcm_mul / self.mmcm_div) / (self.pix_freq.frequency * 5 * self.output_div))))
        print("pixclk {}Mhz, error: {}%. (fclk={}MHz; mul={}; div={}; output_div={})".format(
            self.pix_freq.frequency / 1e6, deviation, self.fclk_freq / 1e6, self.mmcm_mul, self.mmcm_div,
            self.output_div
        ))

        actual_pix_freq = mmcm.output_domain("pix", 5 * self.output_div)
        max_error_freq(actual_pix_freq.frequency, self.pix_freq.frequency)

        mmcm.output_domain("pix5x", self.output_div)

        return m


class TimingGenerator(Elaboratable):
    def __init__(self, video_timing, vertical_signals_shape=range(8000), horizontal_signals_shape=range(4000)):
        self.hscan = ControlSignal(horizontal_signals_shape, reset=video_timing.hscan)
        self.vscan = ControlSignal(vertical_signals_shape, reset=video_timing.vscan)
        self.width = ControlSignal(horizontal_signals_shape, reset=video_timing.hres)
        self.height = ControlSignal(vertical_signals_shape, reset=video_timing.vres)
        self.hsync_start = ControlSignal(horizontal_signals_shape, reset=video_timing.hsync_start)
        self.hsync_end = ControlSignal(horizontal_signals_shape, reset=video_timing.hsync_end)
        self.vsync_start = ControlSignal(vertical_signals_shape, reset=video_timing.vsync_start)
        self.vsync_end = ControlSignal(vertical_signals_shape, reset=video_timing.vsync_end)

        self.x = StatusSignal(horizontal_signals_shape)
        self.y = StatusSignal(vertical_signals_shape)
        self.active = StatusSignal()
        self.hsync = StatusSignal()
        self.vsync = StatusSignal()

    def elaborate(self, plat):
        m = Module()

        # set the xy coordinates
        with m.If(self.x < self.hscan):
            m.d.sync += self.x.eq(self.x + 1)
        with m.Else():
            m.d.sync += self.x.eq(0)
            with m.If(self.y < self.vscan):
                m.d.sync += self.y.eq(self.y + 1)
            with m.Else():
                m.d.sync += self.y.eq(0)

        m.d.comb += [
            self.active.eq((self.x < self.width) & (self.y < self.height)),
            self.hsync.eq((self.x > self.hsync_start) & (self.x <= self.hsync_end)),
            self.vsync.eq((self.y > self.vsync_start) & (self.x <= self.vsync_end))
        ]

        return m


class Rgb(Bundle):
    r = Signal(8)
    g = Signal(8)
    b = Signal(8)


class BertlPatternGenerator(Elaboratable):
    def __init__(self, width, height):
        self.x = Signal.like(width)
        self.y = Signal.like(height)
        self.out = Rgb()

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.out.r.eq(self.x[0:8])
        m.d.comb += self.out.g.eq(self.y[0:8])
        m.d.comb += self.out.b.eq(Cat(Signal(3), self.y[8:10], self.x[8:11]))

        return m


class DimmingPatternGenerator(Elaboratable):
    def __init__(self, width, height):
        self.x = Signal(range(width))
        self.y = Signal(range(height))
        self.out = Rgb()

    def elaborate(self, platform):
        m = Module()

        frame_counter = Signal(range(256 * 3 + 1))
        with m.If((self.x == 0) & (self.y == 0) & (frame_counter < 256 * 3)):
            m.d.sync += frame_counter.eq(frame_counter + 1)
        with m.Elif((self.x == 0) & (self.y == 0)):
            m.d.sync += frame_counter.eq(0)

        with m.If(self.x < 256 * 1):
            m.d.comb += self.out.r.eq(self.x)
        with m.Elif(self.x < 256 * 2):
            m.d.comb += self.out.g.eq(self.x)
        with m.Elif(self.x < 256 * 3):
            m.d.comb += self.out.b.eq(self.x)

        return m
