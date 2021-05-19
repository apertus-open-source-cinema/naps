from nmigen import *
from nmigen.utils import bits_for

from naps import BasicStream, stream_transformer

__all__ = ["StreamMemoryReader"]


class StreamMemoryReader(Elaboratable):
    def __init__(self, address_input: BasicStream, memory: Memory):
        assert len(address_input.payload) == bits_for(memory.depth)
        self.address_input = address_input
        self.memory = memory

        self.output = address_input.clone()
        self.output.payload = Signal(memory.width)

    def elaborate(self, platform):
        m = Module()

        stream_transformer(self.address_input, self.output, m, latency=1, allow_partial_out_of_band=True)
        port = m.submodules.port = self.memory.read_port(domain="sync", transparent=False)
        m.d.comb += port.en.eq(self.address_input.ready & self.address_input.valid)
        m.d.comb += port.addr.eq(self.address_input.payload)
        m.d.comb += self.output.payload.eq(port.data)

        return m
