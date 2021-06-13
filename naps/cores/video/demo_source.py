from nmigen import *

from naps import ControlSignal, StatusSignal
from . import ImageStream, RGB24

__all__ = ["BlinkDemoVideoSource", "BertlDemoVideoSource", "SolidColorDemoVideoSource", "GradientDemoVideoSource"]


class DemoVideoSource(Elaboratable):
    def __init__(self, generator_function, payload_shape, width, height, startup_enable=True):
        self.payload_shape = payload_shape
        self.generator_function = generator_function
        self.enable = ControlSignal(reset=startup_enable)
        self.width = ControlSignal(16, reset=width)
        self.height = ControlSignal(16, reset=height)
        self.frame_counter = StatusSignal(32)

        self.output = ImageStream(payload_shape, name="demo_video_source_output")

    def elaborate(self, platform):
        m = Module()

        x_ctr = Signal(16)
        y_ctr = Signal(16)

        with m.If(self.enable):

            m.d.comb += self.output.valid.eq(1)
            m.d.comb += self.output.payload.eq(
                self.generator_function(m, self, x_ctr, y_ctr, self.frame_counter)
            )
            with m.If(self.output.ready):
                with m.If(x_ctr < self.width - 1):
                    m.d.sync += x_ctr.eq(x_ctr + 1)
                with m.Else():
                    m.d.sync += x_ctr.eq(0)
                    m.d.comb += self.output.line_last.eq(1)
                    with m.If(y_ctr < self.height - 1):
                        m.d.sync += y_ctr.eq(y_ctr + 1)
                    with m.Else():
                        m.d.sync += y_ctr.eq(0)
                        m.d.comb += self.output.frame_last.eq(1)
                        m.d.sync += self.frame_counter.eq(self.frame_counter + 1)

        return m


def BlinkDemoVideoSource(payload_shape, *args, **kwargs):
    def generator_function(m, self, x, y, frame_ctr):
        self.speed = ControlSignal(16, reset=1)
        return Repl((frame_ctr % self.speed) > (self.speed // 2), len(self.output.payload))

    return DemoVideoSource(generator_function, payload_shape, *args, **kwargs)


def BertlDemoVideoSource(*args, **kwargs):
    def generator_function(m, self, x, y, frame_ctr):
        return RGB24(
            r=x[0:8],
            g=y[0:8],
            b=Cat(Signal(3), y[8:10], x[8:11])
        )

    return DemoVideoSource(generator_function, 24, *args, **kwargs)


def SolidColorDemoVideoSource(r=0, g=0, b=0, *args, **kwargs):
    def generator_function(m, self, x, y, frame_ctr):
        self.r = ControlSignal(8, reset=r)
        self.g = ControlSignal(8, reset=g)
        self.b = ControlSignal(8, reset=b)

        return RGB24(r=self.r, g=self.g, b=self.b)

    return DemoVideoSource(generator_function, 24, *args, **kwargs)


def GradientDemoVideoSource(direction_y=True, divider=2, *args, **kwargs):
    def generator_function(m, self, x, y, frame_ctr):
        self.direction_y = ControlSignal(1, reset=direction_y)
        v = Signal(8)
        m.d.comb += v.eq(Mux(self.direction_y, y, x) // divider)
        return RGB24(r=v, g=v, b=v)

    return DemoVideoSource(generator_function, 24, *args, **kwargs)
