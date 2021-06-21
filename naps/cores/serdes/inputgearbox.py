from nmigen import *

from naps import BasicStream, StatusSignal, StreamGearbox, ControlSignal, StreamBuffer


class InputGearbox(Elaboratable):
    def __init__(self, input, output_width):
        self.input = input
        self.output_width = output_width

        self.word_alignment = StatusSignal(range(output_width))

        self.output = BasicStream(output_width)

    def elaborate(self, platform):
        m = Module()

        gearbox = m.submodules.gearbox = StreamGearbox(self.input, self.output_width)
        window = m.submodules.window = StreamWindow(gearbox.output, window_words=2)
        select = m.submodules.select = StreamSelect(window.output, output_width=self.output_width)
        m.d.comb += self.output.connect_upstream(select.output)

        return m


class StreamWindow(Elaboratable):
    """
    Transforms a stream of n bits into a stream of n*m bits with the m last words appended to the current word.
    """

    def __init__(self, input: BasicStream, window_words):
        self.input = input
        self.window_words = window_words
        self.input_len = len(self.input.payload)

        self.output = self.input.clone()
        self.output.payload = Signal(self.input_len * window_words)

    def elaborate(self, platform):
        m = Module()

        last_words = Signal(self.input_len * (self.window_words - 1))
        with m.If(self.input.ready & self.input.valid):
            m.d.sync += last_words.eq(self.output.payload >> self.input_len)

        m.d.comb += self.output.payload.eq((self.input.payload << len(last_words)) | last_words)
        m.d.comb += self.output.connect_upstream(self.input, exclude=['payload'])

        return m


class StreamSelect(Elaboratable):
    """Transforms a Stream of width n to a stream of width m by selecting m bits starting at a variable offset"""

    def __init__(self, input: BasicStream, output_width):
        self.input = input
        self.output_width = output_width

        self.offset = ControlSignal(range(len(self.input.payload) - self.output_width))

        self.output = self.input.clone()
        self.output.payload = Signal(self.output_width)

    def elaborate(self, platform):
        m = Module()

        output = self.output.clone()

        m.d.comb += output.connect_upstream(self.input, exclude=["payload"])
        m.d.comb += output.payload.eq(self.input.payload >> self.offset)

        buffer = m.submodules.buffer = StreamBuffer(output)
        m.d.comb += self.output.connect_upstream(buffer.output)

        return m
