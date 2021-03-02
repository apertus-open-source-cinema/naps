from nmigen import *
from naps import StatusSignal, PacketizedStream
from . import ImageStream

__all__ = ["ImageStream2PacketizedStream", "PacketizedStream2ImageStream"]


class ImageStream2PacketizedStream(Elaboratable):
    """Convert an ImageStream to a packetized Stream by producing one packet per frame"""

    def __init__(self, input: ImageStream):
        self.input = input
        self.output = PacketizedStream(self.input.payload.shape(), name="packetized_image_stream")

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.output.connect_upstream(self.input, exclude=["last", "frame_last", "line_last"])
        m.d.comb += self.output.last.eq(self.input.frame_last)

        return m


class PacketizedStream2ImageStream(Elaboratable):
    """Convert a Packetized stream to an Image stream by creating lines with `width`"""
    def __init__(self, input: PacketizedStream, width):
        self.input = input
        self.width = width
        self.not_exact_number_of_lines_error = StatusSignal(32)
        self.output = ImageStream(input.payload.shape(), name="adapted_image_stream")

    def elaborate(self, platform):
        m = Module()

        line_ctr = Signal(16)

        m.d.comb += self.output.connect_upstream(self.input, only=["ready", "valid", "payload"])
        with m.If(self.input.ready & self.input.valid):
            with m.If(self.input.last):
                m.d.sync += line_ctr.eq(0)
                with m.If(line_ctr != self.width - 1):
                    m.d.sync += self.not_exact_number_of_lines_error.eq(self.not_exact_number_of_lines_error + 1)
            with m.Else():
                with m.If(line_ctr >= (self.width - 1)):
                    m.d.sync += line_ctr.eq(0)
                with m.Else():
                    m.d.sync += line_ctr.eq(line_ctr + 1)

        m.d.comb += self.output.payload.eq(self.input.payload)
        with m.If(self.input.last):
            m.d.comb += self.output.frame_last.eq(1)
            m.d.comb += self.output.line_last.eq(1)
        with m.Else():
            with m.If(line_ctr >= (self.width - 1)):
                m.d.comb += self.output.line_last.eq(1)

        return m
