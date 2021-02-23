from nmigen import *

from nap import ControlSignal, StatusSignal
from . import ImageStream

__all__ = ["BlinkDemoVideoSource"]


class BlinkDemoVideoSource(Elaboratable):
    def __init__(self, payload_shape, width, height):
        self.payload_shape = payload_shape
        self.enable = ControlSignal(reset=1)
        self.width = ControlSignal(16, reset=width)
        self.height = ControlSignal(16, reset=height)
        self.frame_counter = StatusSignal(32)
        self.speed = ControlSignal(16, reset=1)

        self.output = ImageStream(payload_shape, name="test_video_source_output")

    def elaborate(self, platform):
        m = Module()

        x_ctr = Signal(16)
        y_ctr = Signal(16)
        m.d.comb += self.output.valid.eq(1)
        m.d.comb += self.output.payload.eq(Repl((self.frame_counter % self.speed) > (self.speed // 2), len(self.output.payload)))
        with m.If(self.output.ready):
            with m.If(x_ctr < self.width):
                m.d.sync += x_ctr.eq(x_ctr + 1)
            with m.Else():
                m.d.sync += x_ctr.eq(0)
                m.d.comb += self.output.line_last.eq(1)
                with m.If(y_ctr < self.height):
                    m.d.sync += y_ctr.eq(y_ctr + 1)
                with m.Else():
                    m.d.sync += y_ctr.eq(0)
                    m.d.comb += self.output.frame_last.eq(1)
                    with m.If(self.enable):
                        m.d.sync += self.frame_counter.eq(self.frame_counter + 1)
                    with m.Else():
                        m.d.sync += x_ctr.eq(x_ctr)
                        m.d.comb += self.output.valid.eq(0)

        return m
