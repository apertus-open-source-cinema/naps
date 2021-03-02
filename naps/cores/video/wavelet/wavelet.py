from nmigen import *
from naps import ImageStream, DOWNWARDS, BufferedSyncStreamFIFO
from naps.cores.video import ImageSplitter, ImageCombiner, BlackLineGenerator, ImageConvoluter


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

        video_transformer = m.submodules.video_transformer = ImageConvoluter(self.input, transformer_function, self.width, self.height)
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


        def x_preroll(width, stages):
            if stages == 1:
                return 0
            elif stages == 2:
                return width
            else:
                return width * 3 // 4 + x_preroll(width // 2, stages - 1)

        transformer = m.submodules.transformer = Wavelet2D(self.input, self.width, self.height)
        splitter = m.submodules.splitter = ImageSplitter(transformer.output, self.width, self.height)
        for i, output in enumerate(splitter.outputs):
            output.is_hf = Signal(reset=(i != 0)) @ DOWNWARDS

        lf_output = splitter.outputs[0]
        lf_processed = splitter.outputs[0].clone()
        if self.stages == 1:
            m.d.comb += lf_processed.connect_upstream(lf_output)
            m.d.comb += lf_processed.is_hf.eq(0)
        else:
            next_stage_input = lf_output.clone()
            m.d.comb += next_stage_input.connect_upstream(lf_output)
            self.next_stage = next_stage = m.submodules.next_stage = MultiStageWavelet2D(next_stage_input, self.width // 2, self.height // 2, self.stages - 1, self.level + 1)
            padding_generator = m.submodules.padding_generator = BlackLineGenerator(lf_output.payload.shape(), x_preroll(self.width, self.stages), black_value=0) # (2**len(self.input.payload) // 2))

            n_preroll_lines = 5 # TODO(robin): why is it exactly this value
            preroll_lines = Signal(range(n_preroll_lines + 1))
            even_odd = Signal(reset = 1)
            output_counting_stream = lf_processed
            new_line = output_counting_stream.line_last & output_counting_stream.valid & output_counting_stream.ready
            with m.If(preroll_lines < n_preroll_lines):
                with m.If(new_line):
                    m.d.sync += preroll_lines.eq(preroll_lines + 1)
                m.d.comb += lf_processed.connect_upstream(padding_generator.output, allow_partial=True)
            with m.Else():
                with m.If(new_line):
                    m.d.sync += even_odd.eq(~even_odd)
                with m.If(even_odd):
                    m.d.comb += lf_processed.connect_upstream(next_stage.output)
                with m.Else():
                    m.d.comb += lf_processed.connect_upstream(padding_generator.output, allow_partial=True)

        hf_top_right_fifo = m.submodules.hf_topright_fifo = BufferedSyncStreamFIFO(splitter.outputs[1], self.width // 2 - 1)
        hf_combiner = m.submodules.hf_combiner = ImageCombiner(hf_top_right_fifo.output, *splitter.outputs[2:], interleave=True, output_name="hf_combiner_output")
        output_combiner = m.submodules.output_combiner = ImageCombiner(lf_processed, hf_combiner.output, interleave=False, output_name="output_combiner_output")

        if self.level == 1:
            output_buffer_size = 0
        else:
            output_buffer_size = { 2: 5 * self.width // 2 - 4, 1: self.width * 2 - 4 }[self.stages]
        output_fifo = m.submodules.output_fifo = BufferedSyncStreamFIFO(output_combiner.output, output_buffer_size)
        m.d.comb += self.output.connect_upstream(output_fifo.output)

        self.fifos.append(output_fifo)

        return m
