from nmigen import *
from nmigen.lib.fifo import SyncFIFO, AsyncFIFO, AsyncFIFOBuffered

from cores.csr_bank import StatusSignal
from util.stream import StreamEndpoint


class SyncStreamFifo(Elaboratable):
    def __init__(self, input: StreamEndpoint, depth: int):
        assert input.is_sink is False
        self.input = input
        self.output = StreamEndpoint.like(input)
        self.depth = depth

        self.level = StatusSignal(range(depth))
        self.max_level = StatusSignal(range(depth))
        self.overflow_cnt = StatusSignal(32)
        self.underrun_cnt = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        input_sink = StreamEndpoint.like(self.input, is_sink=True)
        m.d.comb += input_sink.connect(self.input)
        if input_sink.has_last:
            fifo_data = Cat(input_sink.payload, input_sink.last)
        else:
            fifo_data = input_sink.payload

        fifo = m.submodules.fifo = SyncFIFO(width=len(fifo_data), depth=self.depth, fwft=False)

        m.d.comb += self.level.eq(fifo.level)
        with m.If(self.level > self.max_level):
            m.d.sync += self.max_level.eq(self.level)

        m.d.comb += input_sink.ready.eq(fifo.w_rdy)
        m.d.comb += fifo.w_data.eq(fifo_data)
        m.d.comb += fifo.w_en.eq(input_sink.valid)

        with m.If(input_sink.valid & (~input_sink.ready)):
            m.d.sync += self.overflow_cnt.eq(self.overflow_cnt + 1)
        with m.If(self.output.ready & (~self.output.valid)):
            m.d.sync += self.underrun_cnt.eq(self.underrun_cnt + 1)

        if self.output.has_last:
            m.d.comb += Cat(self.output.payload, self.output.last).eq(fifo.r_data)
        else:
            m.d.comb += self.output.payload.eq(fifo.r_data)
        m.d.comb += self.output.valid.eq(fifo.r_rdy)
        m.d.comb += fifo.r_en.eq(self.output.ready)

        return m


class AsyncStreamFifo(Elaboratable):
    def __init__(self, input, depth, r_domain, w_domain, buffered=True):
        assert input.is_sink is False
        self.input = input
        self.output = StreamEndpoint.like(input)

        self.r_domain = r_domain
        self.w_domain = w_domain
        self.depth = depth
        self.buffered = buffered

        self.overflow_cnt = StatusSignal(32)
        self.underrun_cnt = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        input_sink = StreamEndpoint.like(self.input, is_sink=True)
        m.d.comb += input_sink.connect(self.input)
        if input_sink.has_last:
            fifo_data = Cat(input_sink.payload, input_sink.last)
        else:
            fifo_data = input_sink.payload

        fifo_type = AsyncFIFOBuffered if self.buffered else AsyncFIFO
        fifo = m.submodules.fifo = fifo_type(width=len(fifo_data), depth=self.depth,
                                             r_domain=self.r_domain, w_domain=self.w_domain, exact_depth=self.depth)

        m.d.comb += input_sink.ready.eq(fifo.w_rdy)
        m.d.comb += fifo.w_data.eq(fifo_data)
        m.d.comb += fifo.w_en.eq(input_sink.valid)

        with m.If(input_sink.valid & (~input_sink.ready)):
            m.d[self.w_domain] += self.overflow_cnt.eq(self.overflow_cnt + 1)
        with m.If(self.output.ready & (~self.output.valid)):
            m.d[self.r_domain] += self.underrun_cnt.eq(self.underrun_cnt + 1)

        if self.output.has_last:
            m.d.comb += Cat(self.output.payload, self.output.last).eq(fifo.r_data)
        else:
            m.d.comb += self.output.payload.eq(fifo.r_data)
        m.d.comb += self.output.valid.eq(fifo.r_rdy)
        m.d.comb += fifo.r_en.eq(self.output.ready)

        return m
