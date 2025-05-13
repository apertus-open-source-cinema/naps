from amaranth import *
from amaranth.lib.fifo import SyncFIFOBuffered, SyncFIFO, AsyncFIFOBuffered, AsyncFIFO
from amaranth.lib.wiring import Component, In, Out
from amaranth.lib.data import ShapeCastable
from amaranth.lib import stream, wiring
from naps import StatusSignal

__all__ = ["BufferedAsyncStreamFIFO", "UnbufferedAsyncStreamFIFO", "BufferedSyncStreamFIFO", "UnbufferedSyncStreamFIFO"]

class StreamFIFO(Component):
    def __init__(self, payload_shape, fifo_type, *, depth, **fifo_args):
        if isinstance(payload_shape, wiring.FlippedInterface):
            payload_shape = wiring.flipped(payload_shape)
        if isinstance(payload_shape, stream.Interface):
            payload_shape = payload_shape.payload

        self.fifo_type = fifo_type
        self.fifo_args = fifo_args
        self.depth = depth
        status_shape = range(depth + 1)

        super().__init__(wiring.Signature({
            "input": In(stream.Signature(payload_shape)),
            "output": Out(stream.Signature(payload_shape)),
            "r_level": Out(status_shape),
            "w_level": Out(status_shape)
        }))

        self.r_level = StatusSignal(status_shape)
        self.w_level = StatusSignal(status_shape)


    def elaborate(self, _):
        m = Module()
        if self.depth == 0:
            wiring.connect(m, wiring.flipped(self.output), wiring.flipped(self.input))
        else:
            fifo = m.submodules.fifo = self.fifo_type(width=len(Value.cast(self.output.p)), depth=self.depth, **self.fifo_args)
            wiring.connect(m, wiring.flipped(self.input), fifo.w_stream)
            wiring.connect(m, wiring.flipped(self.output), fifo.r_stream)
            m.d.comb += self.r_level.eq(fifo.r_level)
            m.d.comb += self.w_level.eq(fifo.w_level)

        return m


def BufferedSyncStreamFIFO(shape, depth, **kwargs):
    return StreamFIFO(shape, SyncFIFOBuffered, depth=depth, **kwargs)


def UnbufferedSyncStreamFIFO(shape, depth, **kwargs):
    return StreamFIFO(shape, SyncFIFO, depth=depth, **kwargs)


def BufferedAsyncStreamFIFO(shape, depth, i_domain="sync", o_domain="sync", exact_depth=False, **kwargs):
    return StreamFIFO(
        shape, AsyncFIFOBuffered, depth=depth, r_domain=o_domain, w_domain=i_domain, exact_depth=exact_depth,
        **kwargs
    )


def UnbufferedAsyncStreamFIFO(shape, depth, i_domain="sync", o_domain="sync", exact_depth=False, **kwargs):
    return StreamFIFO(
        shape, AsyncFIFO, depth=depth, r_domain=o_domain, w_domain=i_domain, exact_depth=exact_depth,
        **kwargs
    )
