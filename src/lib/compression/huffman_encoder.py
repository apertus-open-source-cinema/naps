from nmigen import *
import huffman
from lib.bus.stream.stream import BasicStream
import numpy as np

from lib.compression.bit_stuffing import VariableWidthStream


class HuffmanEncoder(Elaboratable):
    def __init__(self, input: BasicStream, distribution=None, distribution_width=5):
        self.input = input
        self.input_words = 2**len(self.input.payload)

        if distribution is not None:
            self.distribution = distribution
        else:
            x = np.linspace(-distribution_width, distribution_width, self.input_words)
            frequencies = (1 / np.sqrt(2 * np.pi)) * pow(np.e, -0.5 * pow(x, 2))
            self.distribution = list(zip(range(self.input_words), frequencies))
        self.table = {k: v[::-1] for k, v in  huffman.codebook(self.distribution).items()}
        self.max_code_len = max([len(v) for v in self.table.values()])

        self.output = VariableWidthStream(self.max_code_len)

    def elaborate(self, platform):
        m = Module()

        input_transaction = self.input.ready & self.input.valid
        output_transaction = self.output.ready & self.output.valid

        code_memory = Memory(width=self.max_code_len, depth=self.input_words, init=[int(v, 2) for v in self.table.values()])
        code_port = m.submodules.code_port = code_memory.read_port(domain="sync", transparent=False)
        m.d.comb += code_port.en.eq(input_transaction)
        m.d.comb += code_port.addr.eq(self.input.payload)
        m.d.comb += self.output.payload.eq(code_port.data)

        code_len_memory = Memory(width=self.max_code_len, depth=self.input_words, init=[len(v) for v in self.table.values()])
        len_port = m.submodules.len_port = code_len_memory.read_port(domain="sync", transparent=False)
        m.d.comb += len_port.en.eq(input_transaction)
        m.d.comb += len_port.addr.eq(self.input.payload)
        m.d.comb += self.output.current_width.eq(len_port.data)

        output_produce = Signal()
        m.d.sync += output_produce.eq(input_transaction)

        has_output = Signal()
        with m.If(has_output | output_produce):
            m.d.comb += self.output.valid.eq(1)
        m.d.sync += has_output.eq(has_output + output_produce - output_transaction)

        m.d.comb += self.input.ready.eq(self.output.ready)

        return m
