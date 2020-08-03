from itertools import product

from nmigen import *
from nmigen.build import Clock

from cores.hdmi.tmds import Encoder
from .cvt import parse_modeline
from util.nmigen_misc import max_error_freq
from cores.csr_bank import ControlSignal, StatusSignal
from xilinx.io import OSerdes10
from xilinx.ps7 import PS7
from xilinx.clocking import Mmcm
from .rgb import Rgb


class Hdmi(Elaboratable):
    def __init__(self, plugin, modeline, generate_clocks=True):
        self.plugin = plugin
        self.generate_clocks = generate_clocks
        video_timing = parse_modeline(modeline)
        self.pix_freq = Clock(video_timing.pxclk * 1e6)

        self.rgb = Rgb()

        self.hsync_polarity = ControlSignal()
        self.vsync_polarity = ControlSignal()

        self.clock_pattern = ControlSignal(10, name="hdmi_clock_pattern", reset=0b1111100000)

        self.timing_generator = TimingGenerator(video_timing)

    def elaborate(self, platform):
        m = Module()
        if self.generate_clocks:
            self.clocking = m.submodules.clocking = HdmiClocking(self.pix_freq)

        in_pix_domain = DomainRenamer("pix")
        timing = m.submodules.timing_generator = in_pix_domain(self.timing_generator)

        domain_args = {"domain": "pix", "domain_5x": "pix_5x"}
        in_pix_domain = DomainRenamer("pix")

        serializer_clock = m.submodules.serializer_clock = OSerdes10(self.clock_pattern, **domain_args)
        m.d.comb += self.plugin.clock.eq(serializer_clock.output)

        encoder_b = m.submodules.encoder_b = in_pix_domain(
            Encoder(self.rgb.b, Cat(timing.hsync, timing.vsync), timing.active))
        serializer_b = m.submodules.serializer_b = OSerdes10(encoder_b.out, **domain_args)
        m.d.comb += self.plugin.data_b.eq(serializer_b.output)
        encoder_g = m.submodules.encoder_g = in_pix_domain(
            Encoder(self.rgb.g, Cat(timing.hsync, timing.vsync), timing.active))
        serializer_g = m.submodules.serializer_g = OSerdes10(encoder_g.out, **domain_args)
        m.d.comb += self.plugin.data_g.eq(serializer_g.output)
        encoder_r = m.submodules.encoder_r = in_pix_domain(
            Encoder(self.rgb.r, Cat(timing.hsync, timing.vsync), timing.active))
        serializer_r = m.submodules.serializer_r = OSerdes10(encoder_r.out, **domain_args)
        m.d.comb += self.plugin.data_r.eq(serializer_r.output)

        m.submodules.plugin = PluginLowspeedController(self.plugin)

        return m

    def driver_set_modeline(self, modeline):
        video_timing = parse_modeline(modeline)
        self.timing_generator.driver_set_video_timing(video_timing)
        self.clocking.driver_set_pix_clk(video_timing.pxclk * 1e6)


class HdmiClocking(Elaboratable):
    def __init__(self, pix_freq):
        self.pix_freq = pix_freq

    def find_valid_config(self):
        # fast path:
        for output_div in [2, 1, 4, 6]:
            for fclk_frequency in [10e6, 20e6]:
                for mmcm_mul in sorted(Mmcm.vco_multipliers, key=lambda a: abs(a - 39)):
                    if (fclk_frequency * mmcm_mul == self.pix_freq.frequency * 5 * output_div) \
                            and Mmcm.is_valid_vco_conf(fclk_frequency, mmcm_mul, 1):
                        self.mmcm_mul = mmcm_mul
                        self.fclk_freq = fclk_frequency
                        self.output_div = output_div
                        self.mmcm_div = 1
                        return

        # always working path:
        print("WARNING: falling back to slow MMCM calculation path")
        valid_configs = (
            (abs(1 - ((fclk * mul / div) / (self.pix_freq.frequency * 5 * output_div))),
             fclk, mul, div, output_div)
            for fclk, mul, div, output_div in product(
            [f for f in PS7.get_possible_fclk_frequencies() if 1e6 <= f <= 100e6],
            Mmcm.vco_multipliers,
            [1],
            range(1, 6)
        )
            if Mmcm.is_valid_vco_conf(fclk, mul, div)
        )
        deviation, self.fclk_freq, self.mmcm_mul, self.mmcm_div, self.output_div = sorted(valid_configs)[0]

    def elaborate(self, platform):
        m = Module()

        self.find_valid_config()

        platform.ps7.fck_domain(self.fclk_freq, "pix_synth_fclk")
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

        mmcm.output_domain("pix_5x", self.output_div)

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

        self.x = StatusSignal(horizontal_signals_shape, name="x")
        self.y = StatusSignal(vertical_signals_shape, name="y")
        self.active = StatusSignal(name="active")
        self.hsync = StatusSignal(name="hsync")
        self.vsync = StatusSignal(name="vsync")

    def elaborate(self, plat):
        m = Module()

        # set the xy coordinates
        with m.If(self.x < self.hscan - 1):
            m.d.sync += self.x.eq(self.x + 1)
        with m.Else():
            m.d.sync += self.x.eq(0)
            with m.If(self.y < self.vscan - 1):
                m.d.sync += self.y.eq(self.y + 1)
            with m.Else():
                m.d.sync += self.y.eq(0)

        m.d.comb += [
            self.active.eq((self.x < self.width) & (self.y < self.height)),
            self.hsync.eq((self.x >= self.hsync_start) & (self.x < self.hsync_end)),
            self.vsync.eq((self.y >= self.vsync_start) & (self.y < self.vsync_end))
        ]

        return m


class PluginLowspeedController(Elaboratable):
    def __init__(self, plugin):
        self.plugin = plugin

    def elaborate(self, platform):
        m = Module()

        if hasattr(self.plugin, "output_enable"):  # micro style directly connected hdmi plugin module
            sigs = [
                ("output_enable", ControlSignal, 1, 1),
                ("equalizer", ControlSignal, 2, 0b11),
                ("dcc_enable", ControlSignal, 1, 0),
                ("vcc_enable", ControlSignal, 1, 1),
                ("ddet", ControlSignal, 1, 0),
                ("ihp", StatusSignal, 1, 0),
            ]
        elif hasattr(self.plugin, "out_en"):  # zybo style raw hdmi
            sigs = ("out_en", ControlSignal, 1, 1),
        else:
            sigs = []

        # generate low speed CSR signals
        for name, signal_type, width, default in sigs:
            csr_signal = signal_type(width, reset=default)
            setattr(self, name, csr_signal)
            io = getattr(self.plugin, name)
            if signal_type == ControlSignal:
                m.d.comb += io.eq(csr_signal)
            else:
                m.d.comb += csr_signal.eq(io)

        return m