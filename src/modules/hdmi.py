from nmigen import *
from modules.vendor.litevideo_hdmi.s7 import S7HDMIOutPHY
from util.cvt import calculate_video_timing
from modules.managers.clock_manager import generate_clock


class Hdmi(Elaboratable):
    """ A HDMI output block
    excepts to run in the pixclk domain
    """
    def __init__(self, width, height, refresh, pins):
        self.pins = pins
        self.width, self.height, self.refresh = width, height, refresh
        self.pix_clk_freq = calculate_video_timing(width, height, refresh)["pxclk"] * 1e6

    def elaborate(self, plat):
        m = Module()

        pix_clk = generate_clock(self.pix_clk_freq, "pix")
        print(pix_clk)
        generate_clock(pix_clk * 5, "pix5x")

        m.d.comb += self.pins.clock.eq(ClockSignal("pix"))

        t = m.submodules.timing_generator = DomainRenamer("pix")(TimingGenerator(self.width, self.height, self.refresh))
        p = m.submodules.pattern_generator = DomainRenamer("pix")(XorPatternGenerator(self.width, self.height))
        m.d.comb += [
            p.x.eq(t.x),
            p.y.eq(t.y)
        ]

        phy = m.submodules.phy = S7HDMIOutPHY()
        m.d.comb += [
            phy.hsync.eq(t.hsync),
            phy.vsync.eq(t.vsync),
            phy.data_enable.eq(t.active),

            phy.r.eq(p.out.r),
            phy.g.eq(p.out.g),
            phy.b.eq(p.out.b),

            self.pins.data.eq(phy.outputs)
        ]

        return m


class TimingGenerator(Elaboratable):
    def __init__(self, width, height, refresh):
        self.video_timing = calculate_video_timing(width, height, refresh)


        self.x = Signal(max=self.video_timing["hscan"] + 1)
        self.y = Signal(max=self.video_timing["vscan"] + 1)
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
        self.x = Signal(max=width)
        self.y = Signal(max=height)
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
