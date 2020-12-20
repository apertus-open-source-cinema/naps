from nmigen import *
from nmigen.lib.fifo import SyncFIFOBuffered, SyncFIFO, AsyncFIFOBuffered, AsyncFIFO

from lib.bus.stream.stream import Stream
from lib.peripherals.csr_bank import StatusSignal


class StreamFIFO(Elaboratable):
    def __init__(self, input: Stream, fifo_type, **fifo_args):
        self.input = input
        self.output = input.clone(name="fifo_out")
        self.fifo = fifo_type(width=len(Cat(self.input.payload_signals.values())), **fifo_args)
        self.depth = fifo_args['depth']

        self.r_level = StatusSignal(range(self.fifo.depth + 1))
        self.w_level = StatusSignal(range(self.fifo.depth + 1))

    def elaborate(self, platform):
        m = Module()
        fifo = m.submodules.fifo = self.fifo

        if self.depth == 0:
            m.d.comb += self.output.connect_upstream(self.input)
        else:
            m.d.comb += self.r_level.eq(fifo.r_level)
            m.d.comb += self.w_level.eq(fifo.w_level)

            m.d.comb += self.input.ready.eq(fifo.w_rdy)
            m.d.comb += fifo.w_data.eq(Cat(self.input.payload_signals.values()))
            m.d.comb += fifo.w_en.eq(self.input.valid)

            m.d.comb += Cat(self.output.payload_signals.values()).eq(fifo.r_data)
            m.d.comb += self.output.valid.eq(fifo.r_rdy)
            m.d.comb += fifo.r_en.eq(self.output.ready)

        return m


def BufferedSyncStreamFIFO(input: Stream, depth):
    return StreamFIFO(input, SyncFIFO, depth=depth)


def UnbufferedSyncStreamFIFO(input: Stream, depth):
    return StreamFIFO(input, SyncFIFOBuffered, depth=depth)


def BufferedAsyncStreamFIFO(input, depth, i_domain, o_domain, exact_depth=False):
    return StreamFIFO(
        input, AsyncFIFOBuffered, depth=depth, r_domain=o_domain, w_domain=i_domain, exact_depth=exact_depth)


def UnbufferedAsyncStreamFIFO(input, depth, i_domain, o_domain, exact_depth=False):
    return StreamFIFO(
        input, AsyncFIFO, depth=depth, r_domain=o_domain, w_domain=i_domain, exact_depth=exact_depth)
