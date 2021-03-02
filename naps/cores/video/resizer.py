from nmigen import *
from naps import StatusSignal, ControlSignal
from naps.cores import StreamInfo
from . import ImageStream

__all__ = ["VideoResizer"]


class VideoResizer(Elaboratable):
    """Resize an ImageStream by cropping it / extending it with blackness to the desired resolution"""
    def __init__(self, input: ImageStream, desired_width, desired_height):
        self.input = input
        self.output = input.clone(name="resized")

        self.output_width = ControlSignal(16, reset=desired_width)
        self.output_height = ControlSignal(16, reset=desired_height)
        self.shift_x = ControlSignal(signed(16))
        self.shift_y = ControlSignal(signed(16))

        self.input_width = StatusSignal(16)
        self.input_height = StatusSignal(16)

    def elaborate(self, platform):
        m = Module()

        input_x = Signal(16)
        input_y = Signal(16)

        input_read = (self.input.ready & self.input.valid)
        with m.If(input_read):
            with m.If(~self.input.line_last):
                m.d.sync += input_x.eq(input_x + 1)
            with m.Else():
                m.d.sync += input_x.eq(0)
                m.d.sync += self.input_width.eq(input_x + 1)
                m.d.sync += input_y.eq(input_y + 1)
            with m.If(self.input.frame_last):
                m.d.sync += input_y.eq(0)
                m.d.sync += self.input_height.eq(input_y + 1)

        output_x = Signal(16)
        output_y = Signal(16)
        output_write = (self.output.ready & self.output.valid)
        with m.If(output_write):
            with m.If(output_x < self.output_width - 1):
                m.d.sync += output_x.eq(output_x + 1)
            with m.Else():
                m.d.sync += output_x.eq(0)
                m.d.comb += self.output.line_last.eq(1)
                with m.If(output_y < self.output_height - 1):
                    m.d.sync += output_y.eq(output_y + 1)
                with m.Else():
                    m.d.sync += output_y.eq(0)
                    m.d.comb += self.output.frame_last.eq(1)

        eff_x = output_x - self.shift_x
        eff_y = output_y - self.shift_y
        with m.If((eff_x == input_x) & (eff_y == input_y)):
            m.d.comb += self.output.valid.eq(self.input.valid)
            m.d.comb += self.input.ready.eq(self.output.ready)
            m.d.comb += self.output.payload.eq(self.input.payload)
        with m.Elif(((eff_x < input_x) | (eff_y < input_x)) & (eff_x >= 0) & (eff_y >= 0)):
            m.d.comb += self.output.valid.eq(0)
            m.d.comb += self.input.ready.eq(1)
        with m.Else():
            m.d.comb += self.output.valid.eq(1)
            m.d.comb += self.input.ready.eq(0)
            m.d.comb += self.output.payload.eq(0)

        m.submodules.input_stream_info = StreamInfo(self.input)
        m.submodules.output_stream_info = StreamInfo(self.output)

        return m
