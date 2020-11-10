from nmigen import *

from lib.bus.stream.stream import PacketizedStream
from lib.bus.stream.stream_transformer import StreamTransformer
from lib.video.image_stream import ImageStream


class ImageStream2PacketizedStream(Elaboratable):
    """Convert an ImageStream to a packetized Stream by producing one packet per frame"""

    def __init__(self, input: ImageStream):
        self.input = input
        self.output = PacketizedStream(self.input.payload.shape(), name="packetized_image_stream")

    def elaborate(self, platform):
        m = Module()

        with StreamTransformer(self.input, self.output, m):
            m.d.comb += self.output.payload.eq(self.input.payload)
            m.d.comb += self.output.last.eq(self.input.frame_last)

        return m
