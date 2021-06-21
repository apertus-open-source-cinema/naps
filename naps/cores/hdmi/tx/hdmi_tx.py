from itertools import product
from nmigen import *
from nmigen.build import Clock
from naps import ControlSignal, StatusSignal, max_error_freq
from naps.cores import RGB24
from naps.vendor.xilinx_s7 import Mmcm, OSerdes10, PS7
from ..parse_modeline import parse_modeline
from .tmds_encoder import TmdsEncoder

__all__ = ["HdmiTx", "HdmiClocking", "HdmiTimingGenerator", "HdmiPluginLowspeedController"]


class HdmiTx(Elaboratable):
    def __init__(self, resource, modeline, pix_domain="pix", generate_clocks=True):
        self.resource = resource
        self.pix_domain = pix_domain
        self.generate_clocks = generate_clocks
        self.initial_video_timing = parse_modeline(modeline)
        self.pix_freq = Clock(self.initial_video_timing.pxclk * 1e6)

        self.rgb = RGB24()

        self.hsync_polarity = ControlSignal()
        self.vsync_polarity = ControlSignal()

        self.clock_pattern = ControlSignal(10, name="hdmi_clock_pattern", reset=0b1111100000)

        self.timing_generator = HdmiTimingGenerator(self.initial_video_timing)

    def elaborate(self, platform):
        m = Module()
        if self.generate_clocks:
            self.clocking = m.submodules.clocking = HdmiClocking(self.pix_freq, self.pix_domain)

        in_pix_domain = DomainRenamer(self.pix_domain)
        timing = m.submodules.timing_generator = in_pix_domain(self.timing_generator)

        domain_args = {"domain": self.pix_domain, "domain_5x": "{}_5x".format(self.pix_domain)}

        control_char = Signal(2)
        m.d.comb += control_char[0].eq(timing.hsync ^ self.hsync_polarity)
        m.d.comb += control_char[1].eq(timing.vsync ^ self.vsync_polarity)

        encoder_r = m.submodules.encoder_r = in_pix_domain(TmdsEncoder(self.rgb.r, control_char, timing.active))
        encoder_g = m.submodules.encoder_g = in_pix_domain(TmdsEncoder(self.rgb.g, control_char, timing.active))
        encoder_b = m.submodules.encoder_b = in_pix_domain(TmdsEncoder(self.rgb.b, control_char, timing.active))

        serializer_clock = m.submodules.serializer_clock = OSerdes10(self.clock_pattern, self.resource.clock, **domain_args)
        serializer_b = m.submodules.serializer_b = OSerdes10(encoder_b.out, self.resource.b, **domain_args)
        serializer_g = m.submodules.serializer_g = OSerdes10(encoder_g.out, self.resource.g, **domain_args)
        serializer_r = m.submodules.serializer_r = OSerdes10(encoder_r.out, self.resource.r, **domain_args)

        m.submodules.lowspeed = HdmiPluginLowspeedController(self.resource)

        return m


class HdmiClocking(Elaboratable):
    def __init__(self, pix_freq, pix_domain):
        self.pix_domain = pix_domain
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

        platform.ps7.fck_domain(self.fclk_freq, "{}_synth_fclk".format(self.pix_domain))
        mmcm = m.submodules.mmcm = Mmcm(
            input_clock=self.fclk_freq, input_domain="{}_synth_fclk".format(self.pix_domain),
            vco_mul=self.mmcm_mul, vco_div=self.mmcm_div
        )

        deviation = (abs(
            1 - ((self.fclk_freq * self.mmcm_mul / self.mmcm_div) / (self.pix_freq.frequency * 5 * self.output_div))))
        print("pixclk {}Mhz, error: {}%. (fclk={}MHz; mul={}; div={}; output_div={})".format(
            self.pix_freq.frequency / 1e6, deviation, self.fclk_freq / 1e6, self.mmcm_mul, self.mmcm_div,
            self.output_div
        ))

        actual_pix_freq = mmcm.output_domain(self.pix_domain, 5 * self.output_div)
        max_error_freq(actual_pix_freq.frequency, self.pix_freq.frequency)

        mmcm.output_domain("{}_5x".format(self.pix_domain), self.output_div)

        return m


class HdmiTimingGenerator(Elaboratable):
    def __init__(self, video_timing, vertical_signals_shape=range(8000), horizontal_signals_shape=range(4000)):
        self.hscan = ControlSignal(horizontal_signals_shape, reset=video_timing.hscan)
        self.vscan = ControlSignal(vertical_signals_shape, reset=video_timing.vscan)
        self.width = ControlSignal(horizontal_signals_shape, reset=video_timing.hres)
        self.height = ControlSignal(vertical_signals_shape, reset=video_timing.vres)
        self.hsync_start = ControlSignal(horizontal_signals_shape, reset=video_timing.hsync_start)
        self.hsync_end = ControlSignal(horizontal_signals_shape, reset=video_timing.hsync_end)
        self.vsync_start = ControlSignal(vertical_signals_shape, reset=video_timing.vsync_start)
        self.vsync_end = ControlSignal(vertical_signals_shape, reset=video_timing.vsync_end)

        self.x = StatusSignal(horizontal_signals_shape,)
        self.y = StatusSignal(vertical_signals_shape)
        self.active = StatusSignal()
        self.is_blanking_x = StatusSignal()
        self.is_blanking_y = StatusSignal()
        self.hsync = StatusSignal()
        self.vsync = StatusSignal()

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
            self.is_blanking_x.eq(self.x >= self.width),
            self.is_blanking_y.eq(self.y >= self.height),
            self.active.eq((self.x < self.width) & (self.y < self.height)),
            self.hsync.eq((self.x >= self.hsync_start) & (self.x < self.hsync_end)),
            self.vsync.eq((self.y >= self.vsync_start) & (self.y < self.vsync_end))
        ]

        return m


class HdmiPluginLowspeedController(Elaboratable):
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
