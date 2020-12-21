from nmigen import *

from lib.bus.stream.fifo import BufferedSyncStreamFIFO
from lib.data_structure.bundle import DOWNWARDS
from lib.video.image_stream import ImageStream
from lib.video.rearrange import ImageSplitter, ImageCombiner, BlackLineGenerator
from lib.video.video_transformer import VideoTransformer


class Wavelet1D(Elaboratable):
    def __init__(self, input: ImageStream, width, height, direction_y):
        self.input = input
        self.output = ImageStream(input.payload.shape(), name="wavelet_1D_output")

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
                m.d.comb += output.eq(((px(0) - px(1) + (-px(-2) - px(-1) + px(2) + px(3)) // 8) // 2) + (2**len(self.input.payload) // 2))
            return output

        video_transformer = m.submodules.video_transformer = VideoTransformer(self.input, transformer_function, self.width, self.height)
        m.d.comb += self.output.connect_upstream(video_transformer.output)

        return m


class Wavelet2D(Elaboratable):
    def __init__(self, input: ImageStream, width, height):
        self.input = input
        self.output = ImageStream(input.payload.shape(), name="wavelet_2D_output")

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
    def __init__(self, input: ImageStream, width, height, stages, level=1):
        self.input = input
        self.output = input.clone(name="wavelet_level{}_output".format(level))
        self.output.is_hf = Signal() @ DOWNWARDS

        self.width = width
        self.level = level
        self.height = height
        self.stages = stages
        self.fifos = []

    def elaborate(self, platform):
        m = Module()

        def calculate_needed_bottom_buffer(stage):
            if stage == 1:
                return 0
            else:
                return 6 * (self.width // 2**(stage - 1)) + calculate_needed_bottom_buffer(stage - 1)


        transformer = m.submodules.transformer = Wavelet2D(self.input, self.width, self.height)
        splitter = m.submodules.splitter = ImageSplitter(transformer.output, self.width, self.height)
        for i, output in enumerate(splitter.outputs):
            output.is_hf = Signal(reset=(i != 0)) @ DOWNWARDS

        stretch_factor = (2 ** (self.stages - 1))

        lf_output = splitter.outputs[0]
        lf_processed = splitter.outputs[0].clone()
        if self.stages == 1:
            lf_final_fifo = m.submodules.lf_final_fifo = BufferedSyncStreamFIFO(lf_output, 0)
            self.fifos.append(lf_final_fifo)
            m.d.comb += lf_processed.connect_upstream(lf_final_fifo.output)
            m.d.comb += lf_processed.is_hf.eq(0)
        else:
            next_stage_input = lf_output.clone()
            m.d.comb += next_stage_input.connect_upstream(lf_output)
            self.next_stage = next_stage = m.submodules.next_stage = MultiStageWavelet2D(next_stage_input, self.width // 2, self.height // 2, self.stages - 1, self.level + 1)
            padding_generator = m.submodules.padding_generator = BlackLineGenerator(lf_output.payload.shape(), self.width // 2 * stretch_factor, black_value=(2**len(self.input.payload) // 2))

            n_preroll_lines = 6 # TODO: this is bs. why does it work
            preroll_lines = Signal(range(n_preroll_lines + 1))
            with m.If(preroll_lines < n_preroll_lines):
                with m.If(next_stage_input.line_last & next_stage_input.valid & next_stage_input.ready):  # TODO: see above; should be lf_processed.*
                    m.d.sync += preroll_lines.eq(preroll_lines + 1)
                m.d.comb += lf_processed.connect_upstream(padding_generator.output, allow_partial=True)
            with m.Else():
                m.d.comb += lf_processed.connect_upstream(next_stage.output)

        hf_fifo_depths = [self.width // 2 - 1, 0, 0]
        hf_fifos = [BufferedSyncStreamFIFO(s, depth) for s, depth in zip(splitter.outputs[1:], hf_fifo_depths)]
        m.submodules += hf_fifos
        hf_outputs = [fifo.output for fifo in hf_fifos]
        hf_combiner = m.submodules.hf_combiner = ImageCombiner(*hf_outputs, interleave=True, output_name="hf_combiner_output")
        # we stretch the hf part that would occupy multiple lines of the now downscaled image (from a subsequent level) into one long line
        hf_stretcher = m.submodules.hf_stretcher = ImageCombiner(*([hf_combiner.output] * stretch_factor), interleave=False, output_name="hf_stretcher_output")
        output_combiner = m.submodules.output_combiner = ImageCombiner(lf_processed, hf_stretcher.output, interleave=False, output_name="output_combiner_output")

        if self.level == 1:
            output_buffer_size = 0
        else:
            output_buffer_size = { 2: self.width * 4, 1: self.width * 4 - 6 }[self.stages] # self.width * (2 ** self.level)
            # print(f"level: {self.level}, buffersize: {output_buffer_size}")
        output_fifo = m.submodules.output_fifo = BufferedSyncStreamFIFO(output_combiner.output, output_buffer_size)
        m.d.comb += self.output.connect_upstream(output_fifo.output)

        self.fifos.append(output_fifo)

        return m
