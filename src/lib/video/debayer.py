from nmigen import *

from lib.bus.stream.stream_transformer import StreamTransformer
from lib.peripherals.csr_bank import ControlSignal
from lib.video.image_stream import ImageStream
from lib.video.rgb import RGB


class SimpleFullResDebayerer(Elaboratable):
    def __init__(self, input: ImageStream):
        self.input = input
        self.output = ImageStream(24)

        self.shift_x = ControlSignal()
        self.shift_y = ControlSignal()

    def elaborate(self, platform):
        m = Module()

        x_odd = Signal()
        y_odd = Signal()
        with StreamTransformer(self.input, self.output, m):
            with m.If(self.input.line_last):
                m.d.comb += self.output.line_last.eq(1)
                m.d.sync += x_odd.eq(0)
                m.d.sync += y_odd.eq(~y_odd)
            with m.Else():
                m.d.sync += x_odd.eq(~x_odd)
            with m.If(self.input.frame_last):
                m.d.comb += self.output.frame_last.eq(1)
                m.d.sync += y_odd.eq(0)
                m.d.sync += x_odd.eq(0)

        x = x_odd ^ self.shift_x
        y = y_odd ^ self.shift_y

        val = Signal(8)
        m.d.comb += val.eq(self.input.payload >> 4)

        rgb = RGB()
        with m.If(x & ~y):
            m.d.comb += rgb.r.eq(val)
        with m.If(~x & y):
            m.d.comb += rgb.b.eq(val)
        with m.Else():
            m.d.comb += rgb.g.eq(val // 2)

        m.d.comb += self.output.payload.eq(rgb)

        return m
