from nmigen import *

from lib.video.image_stream import ImageStream


class ImageProxy:
    def __init__(self, shape, x_signal, y_signal):
        self.y_signal = y_signal
        self.x_signal = x_signal
        self.shape = shape
        self.expr_mapping = {}

    def __getitem__(self, item):
        if item not in self.expr_mapping:
            self.expr_mapping[item] = Signal(self.shape)

        return self.expr_mapping[item]



class VideoTransformer(Elaboratable):
    def __init__(self, input: ImageStream, transformer_function, max_width=3000, max_height=3000):
        self.input = input
        self.max_width = max_width

        self.transformer_m = Module()
        self.image_proxy = ImageProxy()
        self.x = Signal()
        self.y = Signal()
        self.output_payload = transformer_function(self.x, self.y, self.image_proxy, self.transformer_m)

        self.output = ImageStream(self.output_payload.shape, name="video_transformer_output")

    def elaborate(self, platform):
        m = Module()

        return m
