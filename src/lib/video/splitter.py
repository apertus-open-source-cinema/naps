from nmigen import *

from lib.video.image_stream import ImageStream


class ImageStreamSplitter(Elaboratable):
    """Splits each image in four sub images. From each 4x4 pixel cluster each image receives one pixel. This can eg. be handy to decompose bayer data."""
    def __init__(self, input: ImageStream):
        self.input = input

        self.output_top_left = input.clone()
        self.output_top_right = input.clone()
        self.output_bottom_left = input.clone()
        self.output_bottom_right = input.clone()

    def elaborate(self, platform):
        m = Module()

        x = Signal(16)
        y = Signal(16)

        # we need to delay the data one cycle to be able to generate correct last signals
        last_top_left = Signal.like(self.input.payload)
        last_top_right = Signal.like(self.input.payload)
        last_bottom_left = Signal.like(self.input.payload)
        last_bottom_right = Signal.like(self.input.payload)

        input_read = (self.input.ready & self.input.valid)
        with m.If(input_read):
            with m.If(~self.input.line_last):
                m.d.sync += x.eq(x + 1)
            with m.Else():
                m.d.sync += x.eq(0)
                m.d.sync += y.eq(y + 1)
            with m.If(self.input.frame_last):
                m.d.sync += y.eq(0)

            with m.If((x % 2 == 0) & (y % 2 == 0)):
                m.d.sync += last_top_left.eq(self.input.payload)
                m.d.comb += self.output_top_left.payload.eq(last_top_left)
            with m.Elif((x % 2 == 1) & (y % 2 == 0)):
                m.d.sync += last_top_right.eq(self.input.payload)
                m.d.comb += self.output_top_right.payload.eq(last_top_right)
            with m.Elif((x % 2 == 0) & (y % 2 == 1)):
                m.d.sync += last_bottom_left.eq(self.input.payload)
                m.d.comb += self.output_bottom_left.payload.eq(last_bottom_left)
            with m.Elif((x % 2 == 1) & (y % 2 == 1)):
                m.d.sync += last_bottom_right.eq(self.input.payload)
                m.d.comb += self.output_bottom_right.payload.eq(last_bottom_right)

        with m.If(self.input.valid):
            with m.If((x % 2 == 0) & (y % 2 == 0)):
                m.d.comb += self.input.ready.eq(self.output_top_left.ready)
                m.d.comb += self.output_top_left.valid.eq(1)
            with m.Elif((x % 2 == 1) & (y % 2 == 0)):
                m.d.comb += self.input.ready.eq(self.output_top_right.ready)
                m.d.comb += self.output_top_right.valid.eq(1)
            with m.Elif((x % 2 == 0) & (y % 2 == 1)):
                m.d.comb += self.input.ready.eq(self.output_bottom_left.ready)
                m.d.comb += self.output_bottom_left.valid.eq(1)
            with m.Elif((x % 2 == 1) & (y % 2 == 1)):
                m.d.comb += self.input.ready.eq(self.output_bottom_right.ready)
                m.d.comb += self.output_bottom_left.valid.eq(1)

        return m