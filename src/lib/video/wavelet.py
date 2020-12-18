from nmigen import *

from lib.video.image_stream import ImageStream
from lib.video.video_transformer import VideoTransformer


class Wavelet1D(Elaboratable):
    def __init__(self, input: ImageStream, width, height, direction_y):
        self.input = input
        self.output = input.clone()

        self.height = height
        self.width = width
        self.direction_y = direction_y

    def elaborate(self, platform):
        m = Module()

        def transformer_function(x, y, image_proxy):
            output = Signal.like(image_proxy[x, y])

            def px(shift):
                if self.direction_y:
                    return image_proxy[x, y + shift]
                else:
                    return image_proxy[x + shift, y]

            # even pixels are lf while odd pixels are hf
            with m.If((y if self.direction_y else x) % 2 == 0):
                m.d.comb += output.eq((px(0) + px(1)) // 2)
            with m.Else():
                m.d.comb += output.eq(((px(0) - px(1) + (-px(-2) - px(-1) + px(2) + px(3)) // 8) // 2) + 127)
            return output

        video_transformer = m.submodules.video_transformer = VideoTransformer(self.input, transformer_function,
                                                                              self.width, self.height)
        m.d.comb += self.output.connect_upstream(video_transformer.output)

        return m


class Wavelet2D(Elaboratable):
    def __init__(self, input: ImageStream, width, height):
        self.input = input
        self.output = input.clone(name="wavelet_output")

        self.height = height
        self.width = width

    def elaborate(self, platform):
        m = Module()

        wavelet_x = m.submodules.wavelet_x = Wavelet1D(self.input, self.width, self.height, direction_y=False)
        wavelet_y = m.submodules.wavelet_y = Wavelet1D(wavelet_x.output, self.width, self.height, direction_y=True)
        m.d.comb += self.output.connect_upstream(wavelet_y.output)

        return m
