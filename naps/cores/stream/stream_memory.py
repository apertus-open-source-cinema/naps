from amaranth import *
from amaranth.lib import wiring, stream
from amaranth.lib.memory import Memory
from amaranth.lib.wiring import Component, In, Out
from amaranth.utils import bits_for


__all__ = ["StreamMemoryReader"]

from naps import substitute_payload, real_payload
from naps.stream.stream_transformer import stream_transformer


class StreamMemoryReader(Component):
    def __init__(self, memory: Memory, address_shape = None):
        if address_shape is None:
            address_shape = range(memory.depth)
        super().__init__(wiring.Signature({
            "input": In(stream.Signature(address_shape)),
            "output": Out(stream.Signature(substitute_payload(address_shape, memory.shape)))
        }))
        self.memory = memory

    def elaborate(self, platform):
        m = Module()

        input_transaction = stream_transformer(m, self.input, self.output, latency=1)
        port = self.memory.read_port(domain="sync")
        m.d.comb += port.en.eq(input_transaction)
        m.d.comb += port.addr.eq(real_payload(self.input.p))
        m.d.comb += real_payload(self.output.p).eq(port.data)

        return m
