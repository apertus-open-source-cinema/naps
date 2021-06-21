from nmigen import *
from naps import nAny, iterator_with_if_elif, StatusSignal
from . import ImageStream

__all__ = ["ImageSplitter", "ImageSplitter2", "ImageCombiner", "BlackLineGenerator"]


class ImageSplitter(Elaboratable):
    """Splits each image in four sub images. From each 4x4 pixel cluster each image receives one pixel. This can eg. be handy to decompose bayer data."""

    def __init__(self, input: ImageStream, width, height):
        self.input = input

        self.output_top_left = input.clone()
        self.output_top_right = input.clone()
        self.output_bottom_left = input.clone()
        self.output_bottom_right = input.clone()
        self.outputs = [self.output_top_left, self.output_top_right, self.output_bottom_left, self.output_bottom_right]
        self.output_shifts = [(0, 0), (1, 0), (0, 1), (1, 1)]

        self.width = width
        self.height = height

    def elaborate(self, platform):
        m = Module()

        input_transaction = Signal()
        m.d.comb += input_transaction.eq(self.input.ready & self.input.valid)

        x = Signal(16)
        y = Signal(16)
        with m.If(input_transaction):
            with m.If(~self.input.line_last):
                m.d.sync += x.eq(x + 1)
            with m.Else():
                m.d.sync += x.eq(0)
                m.d.sync += y.eq(y + 1)
            with m.If(self.input.frame_last):
                m.d.sync += y.eq(0)

        output_transaction = Signal()
        m.d.comb += output_transaction.eq(nAny(s.ready & s.valid for s in self.outputs))

        for cond, (output, shift) in iterator_with_if_elif(zip(self.outputs, self.output_shifts), m):
            with cond((x % 2 == shift[0]) & (y % 2 == shift[1])):
                m.d.comb += self.input.ready.eq(output.ready)
                m.d.comb += output.valid.eq(self.input.valid)
                m.d.comb += output.payload.eq(self.input.payload)
                # the last signals are used as first signals here and are later converted
                m.d.comb += output.line_last.eq((x // 2) == (self.width - 1) // 2)
                m.d.comb += output.frame_last.eq(((y // 2) == (self.height - 1) // 2) & output.line_last)

        return m


class ImageSplitter2(Elaboratable):
    """Splits an Image into n chunks horizontally"""
    def __init__(self, input: ImageStream, chunk_width, n_chunks, height):
        self.chunk_width = chunk_width
        self.height = height
        self.n_chunks = n_chunks
        self.input = input

        self.x_ctr = StatusSignal(16)
        self.y_ctr = StatusSignal(16)

        self.outputs = [self.input.clone(f'splitter_output_{i}') for i in range(n_chunks)]

    def elaborate(self, platform):
        m = Module()

        with m.If(self.input.ready & self.input.valid):
            m.d.sync += self.x_ctr.eq(self.x_ctr + 1)
            with m.If(self.input.line_last):
                m.d.sync += self.x_ctr.eq(0)
                m.d.sync += self.y_ctr.eq(self.y_ctr + 1)
            with m.If(self.input.frame_last):
                m.d.sync += self.y_ctr.eq(0)

        for i, output in enumerate(self.outputs):
            start, end = i * self.chunk_width, (i + 1) * self.chunk_width
            m.d.comb += self.input.ready.eq(1)  # if noone is responsible, we dont hang everything
            with m.If((self.x_ctr >= start) & (self.x_ctr < end)):
                m.d.comb += output.connect_upstream(self.input, exclude=['frame_last', 'line_last'])
                m.d.comb += output.line_last.eq(self.x_ctr == end - 1)
                m.d.comb += output.frame_last.eq((self.x_ctr == end - 1) & (self.y_ctr == self.height - 1))
            

        return m


class ImageCombiner(Elaboratable):
    """Combines image streams to a larger image stream by either putting them side by side or interleaving them.
     May deadlock if the input streams are not enough buffered."""
    def __init__(self, *inputs: ImageStream, interleave=True, output_name=None):
        self.inputs = inputs
        assert all(input.payload.shape() == inputs[0].payload.shape() for input in inputs)
        self.output = inputs[0].clone(name=output_name)
        self.interleave = interleave

    def elaborate(self, platform):
        m = Module()

        output_transaction = Signal()
        m.d.comb += output_transaction.eq(self.output.ready & self.output.valid)

        with m.FSM():
            for i, input in enumerate(self.inputs):
                with m.State(str(i)):
                    m.d.comb += input.ready.eq(self.output.ready)
                    m.d.comb += self.output.valid.eq(input.valid)
                    m.d.comb += self.output.payload.eq(input.payload)
                    m.d.comb += self.output.line_last.eq(input.line_last & (i == len(self.inputs) - 1))
                    m.d.comb += self.output.frame_last.eq(input.frame_last & (i == len(self.inputs) - 1))
                    with m.If(self.interleave & output_transaction):
                        m.next = str((i + 1) % len(self.inputs))
                    with m.If((not self.interleave) & output_transaction & input.line_last):
                        m.next = str((i + 1) % len(self.inputs))

        return m


class BlackLineGenerator(Elaboratable):
    """generates a frame of infinite height and defined length. the generated frame is all black"""
    def __init__(self, payload_shape, width, black_value=0):
        self.output = ImageStream(payload_shape, name="black_lines_output")
        self.width = width
        self.black_value = black_value

    def elaborate(self, platform):
        m = Module()

        line_counter = Signal(range(self.width))
        m.d.comb += self.output.valid.eq(1)
        m.d.comb += self.output.payload.eq(self.black_value)
        with m.If(self.output.ready):
            with m.If(line_counter < self.width - 1):
                m.d.sync += line_counter.eq(line_counter + 1)
            with m.Else():
                m.d.sync += line_counter.eq(0)
                m.d.comb += self.output.line_last.eq(1)

        return m