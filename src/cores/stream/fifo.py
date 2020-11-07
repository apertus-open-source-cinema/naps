from nmigen import *
from nmigen.lib.fifo import SyncFIFOBuffered, SyncFIFO, AsyncFIFOBuffered, AsyncFIFO

from cores.csr_bank import StatusSignal
from util.stream import Stream


class SyncStreamFifo(Elaboratable):
    def __init__(self, input: Stream, depth: int, buffered=True, fwtf=False):
        self.input = input
        self.output = Stream.like(input)
        self.depth = depth
        self.buffered = buffered
        self.fwtf = fwtf

        self.max_w_level = StatusSignal(range(depth))
        self.r_level = StatusSignal(range(depth + 1))
        self.w_level = StatusSignal(range(depth + 1))

    def elaborate(self, platform):
        m = Module()

        if hasattr(self.input, "last"):
            fifo_data = Cat(self.input.payload, self.input.last)
        else:
            fifo_data = self.input.payload

        if self.buffered:
            assert not self.fwtf
            fifo = m.submodules.fifo = SyncFIFOBuffered(width=len(fifo_data), depth=self.depth)
        else:
            fifo = m.submodules.fifo = SyncFIFO(width=len(fifo_data), depth=self.depth, fwft=self.fwtf)

        m.d.comb += self.r_level.eq(fifo.r_level)
        m.d.comb += self.w_level.eq(fifo.w_level)

        with m.If(self.w_level > self.max_w_level):
            m.d.sync += self.max_w_level.eq(self.w_level)

        m.d.comb += self.input.ready.eq(fifo.w_rdy)
        m.d.comb += fifo.w_data.eq(fifo_data)
        m.d.comb += fifo.w_en.eq(self.input.valid)

        if hasattr(self.output, "last"):
            m.d.comb += Cat(self.output.payload, self.output.last).eq(fifo.r_data)
        else:
            m.d.comb += self.output.payload.eq(fifo.r_data)
        m.d.comb += self.output.valid.eq(fifo.r_rdy)
        m.d.comb += fifo.r_en.eq(self.output.ready)

        return m


class AsyncStreamFifo(Elaboratable):
    def __init__(self, input, depth, r_domain, w_domain, buffered=True, exact_depth=False):
        self.input = input
        self.output = Stream.like(input)

        self.r_domain = r_domain
        self.w_domain = w_domain
        self.depth = depth
        self.exact_depth = exact_depth
        self.buffered = buffered

        self.r_level = StatusSignal(range(depth + 1))
        self.w_level = StatusSignal(range(depth + 1))

    def elaborate(self, platform):
        m = Module()

        if hasattr(self.input, "last"):
            fifo_data = Cat(self.input.payload, self.input.last)
        else:
            fifo_data = self.input.payload

        fifo_type = AsyncFIFOBuffered if self.buffered else AsyncFIFO
        fifo = m.submodules.fifo = fifo_type(width=len(fifo_data), depth=self.depth,
                                             r_domain=self.r_domain, w_domain=self.w_domain, exact_depth=self.exact_depth)

        m.d.comb += self.r_level.eq(fifo.r_level)
        m.d.comb += self.w_level.eq(fifo.w_level)

        m.d.comb += self.input.ready.eq(fifo.w_rdy)
        m.d.comb += fifo.w_data.eq(fifo_data)
        m.d.comb += fifo.w_en.eq(self.input.valid)

        if hasattr(self.output, "last"):
            m.d.comb += Cat(self.output.payload, self.output.last).eq(fifo.r_data)
        else:
            m.d.comb += self.output.payload.eq(fifo.r_data)
        m.d.comb += self.output.valid.eq(fifo.r_rdy)
        m.d.comb += fifo.r_en.eq(self.output.ready)

        return m
