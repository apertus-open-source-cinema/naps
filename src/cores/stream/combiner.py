from nmigen import *

from cores.csr_bank import StatusSignal
from cores.stream.stream import StreamEndpoint


class StreamCombiner(Elaboratable):
    def __init__(self, streams):
        self._streams = streams

        self.has_last = self._streams[0].has_last
        assert not any(self.has_last is not other.has_last for other in self._streams)

        width = sum(len(stream.payload) for stream in self._streams)
        self.output = StreamEndpoint(payload=Signal(width), is_sink=False, last=self.has_last)

        self.different_last_error = StatusSignal()
        self.different_valid_error = StatusSignal()

    def elaborate(self, platform):
        m = Module()

        highest_bit = 0
        for stream in self._streams:
            sink = StreamEndpoint.like(stream, is_sink=True)
            sink.connect(stream)
            m.d.comb += stream.ready.eq(self.output.ready)
            m.d.comb += self.output.payload[highest_bit:highest_bit + len(stream.payload)].eq(stream.payload)
            highest_bit += len(stream.payload)

            m.d.comb += self.output.valid.eq(stream.valid)
            with m.If(self.output.valid != stream.valid):
                m.d.sync += self.different_valid_error.eq(1)

            if self.has_last:
                m.d.comb += self.output.last.eq(stream.last)
                with m.If(self.output.last != stream.last):
                    m.d.sync += self.different_last_error.eq(1)

        return m
