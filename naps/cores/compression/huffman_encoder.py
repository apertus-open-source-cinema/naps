import huffman
from amaranth import *
from amaranth.lib.memory import Memory
from naps import PacketizedStream, stream_transformer
from . import VariableWidthStream

__all__ = ["HuffmanEncoder"]


class HuffmanEncoder(Elaboratable):
    def __init__(self, input: PacketizedStream, distribution):
        self.input = input

        self.distribution = distribution
        self.table = {k: v[::-1] for k, v in huffman.codebook(self.distribution.items()).items()}

        self.max_input_word = max(self.distribution.keys()) + 1
        self.max_code_len = max([len(v) for v in self.table.values()])

        self.output = VariableWidthStream(self.max_code_len + 1)

    def elaborate(self, platform):
        m = Module()

        # this code is kind of similar to the StreamMemoryReader but not quite the same as it operates two memories at the same time
        stream_transformer(self.input, self.output, m, latency=1, allow_partial_out_of_band=True)
        input_transaction = self.input.ready & self.input.valid

        code_memory = m.submodules.code_memory = Memory(shape=self.max_code_len, depth=self.max_input_word, init=[int(self.table.get(i, '0'), 2) for i in range(self.max_input_word)])
        code_port = code_memory.read_port(domain="sync")
        m.d.comb += code_port.en.eq(input_transaction)
        m.d.comb += code_port.addr.eq(self.input.payload)
        m.d.comb += self.output.payload.eq(code_port.data)

        m.submodules.code_len_memory = code_len_memory = Memory(shape=self.max_code_len, depth=self.max_input_word, init=[len(self.table.get(i, '')) for i in range(self.max_input_word)])
        len_port = code_len_memory.read_port(domain="sync")
        m.d.comb += len_port.en.eq(input_transaction)
        m.d.comb += len_port.addr.eq(self.input.payload)
        m.d.comb += self.output.current_width.eq(len_port.data)

        return m
