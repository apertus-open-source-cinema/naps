from nmigen import *

from util.stream import StreamEndpoint


class StreamCounterDebugTool(Elaboratable):
    def __init__(self, input_stream: StreamEndpoint):
        """
        takes a stream and fills the upper half of the stream with a counter to verify that no data is lost.
        """
        assert input_stream.payload.width % 2 == 0, "the input stream width must be divisabe two"
        self.input_stream = input_stream
        self.output = StreamEndpoint.like(input_stream, is_sink=False)

    def elaborate(self, platform):
        m = Module()

        input_sink = StreamEndpoint.like(self.input_stream, is_sink=True, name="ft601_sink")
        m.d.comb += input_sink.connect(self.input_stream)

        counter = Signal(input_sink.payload.width // 2)
        with m.If(self.input_stream.valid):
            m.d.sync += counter.eq(counter + 1)

        m.d.comb += self.input_stream.ready.eq(self.output.ready)
        m.d.comb += self.output.valid.eq(self.input_stream.valid)
        m.d.comb += self.output.eq(Cat(input_sink.payload[:input_sink.payload.width // 2], counter))

        return m