from nmigen import *

from lib.bus.stream.fifo import BufferedSyncStreamFIFO
from lib.video.image_stream import ImageStream
from lib.video.splitter import ImageSplitter, ImageCombiner
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


class MultiStageWavelet2D(Elaboratable):
    """Does a multi level wavelet transform while producing a wide image that has the lf part on the left and the hf parts on the right"""
    def __init__(self, input: ImageStream, width, height, stages):
        self.input = input
        self.output = input.clone()

        self.width = width
        self.height = height
        self.stages = stages

    def elaborate(self, platform):
        m = Module()

        def calculate_needed_bottom_buffer(stage):
            if stage == 1:
                return 0
            else:
                return 6 * (self.width // 2**(stage - 1)) * calculate_needed_bottom_buffer(stage - 1)

        transformer = m.submodules.transformer = Wavelet2D(self.input, self.width, self.height)
        splitter = m.submodules.splitter = ImageSplitter(transformer.output, self.width, self.height)
        fifo_depths = [
            self.width // 2 + calculate_needed_bottom_buffer(self.stages),
            self.width // 2 + calculate_needed_bottom_buffer(self.stages),
            calculate_needed_bottom_buffer(self.stages),
            calculate_needed_bottom_buffer(self.stages)
        ]
        print(fifo_depths)
        fifos = [BufferedSyncStreamFIFO(s, depth) for s, depth in zip(splitter.outputs, fifo_depths)]
        fifo_outputs = [fifo.output for fifo in fifos]
        for fifo in fifos:
            m.submodules += fifo

        lf_output = fifo_outputs[0]
        hf_outputs = fifo_outputs[1:]

        hf_combiner1 = m.submodules.hf_combiner1 = ImageCombiner(hf_outputs[1], hf_outputs[2], interleave=True)
        hf_combiner2 = m.submodules.hf_combiner2 = ImageCombiner(hf_outputs[0], hf_combiner1.output, interleave=False)
        if self.stages == 1:
            lf_out = lf_output
        else:
            next_stage = m.submodules.next_stage = MultiStageWavelet2D(lf_output, self.width // 2, self.height // 2, self.stages - 1)
            lf_out = next_stage.output
        # we stretch the hf part that would occupy multiple lines of the now downscaled image (from a subsequent level) into one long line
        hf_stretcher = m.submodules.hf_stretcher = ImageCombiner(*([hf_combiner2.output] * (2 ** (self.stages - 1))), interleave=False)
        output_combiner = m.submodules.output_combiner = ImageCombiner(lf_out, hf_stretcher.output, interleave=False)

        m.d.comb += self.output.connect_upstream(output_combiner.output)

        return m
