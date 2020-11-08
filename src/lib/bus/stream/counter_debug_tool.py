from nmigen import *

from lib.bus.stream.stream import Stream


class StreamCounterDebugTool(Elaboratable):
    def __init__(self, input: Stream):
        """
        takes a stream and fills the upper half of the stream with a counter to verify that no data is lost.
        """
        assert input.payload.width % 2 == 0, "the input stream width must be divisabe two"
        self.input = input
        self.output = Stream.like(input)

    def elaborate(self, platform):
        m = Module()

        counter = Signal(self.input.payload.width // 2)
        with m.If(self.input.valid):
            m.d.sync += counter.eq(counter + 1)

        m.d.comb += self.input.ready.eq(self.output.ready)
        m.d.comb += self.output.valid.eq(self.input.valid)
        m.d.comb += self.output.payload.eq(Cat(self.input.payload[:self.input.payload.width // 2], counter))

        return m