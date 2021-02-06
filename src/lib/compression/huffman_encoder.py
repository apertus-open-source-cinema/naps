from nmigen import *
import huffman
from lib.bus.stream.stream import BasicStream
from lib.compression.bit_stuffing import VariableWidthStream


class HuffmanEncoder(Elaboratable):
    def __init__(self, input: BasicStream, distribution):
        self.input = input

        self.distribution = distribution
        self.table = {k: v[::-1] for k, v in  huffman.codebook(self.distribution.items()).items()}

        self.max_input_word = max(self.distribution.keys()) + 1
        self.max_code_len = max([len(v) for v in self.table.values()])

        self.output = VariableWidthStream(self.max_code_len + 1)

    def elaborate(self, platform):
        m = Module()

        input_transaction = self.input.ready & self.input.valid
        output_transaction = self.output.ready & self.output.valid

        with m.If(input_transaction):
            for k in self.input.out_of_band_signals.keys():
                m.d.sync += getattr(self.output, k).eq(getattr(self.input, k))

        code_memory = Memory(width=self.max_code_len, depth=self.max_input_word, init=[int(self.table.get(i, '0'), 2) for i in range(self.max_input_word)])
        code_port = m.submodules.code_port = code_memory.read_port(domain="sync", transparent=False)
        m.d.comb += code_port.en.eq(input_transaction)
        m.d.comb += code_port.addr.eq(self.input.payload)
        m.d.comb += self.output.payload.eq(code_port.data)

        code_len_memory = Memory(width=self.max_code_len, depth=self.max_input_word, init=[len(self.table.get(i, '')) for i in range(self.max_input_word)])
        len_port = m.submodules.len_port = code_len_memory.read_port(domain="sync", transparent=False)
        m.d.comb += len_port.en.eq(input_transaction)
        m.d.comb += len_port.addr.eq(self.input.payload)
        m.d.comb += self.output.current_width.eq(len_port.data)

        output_produce = Signal()
        m.d.sync += output_produce.eq(input_transaction)

        has_output = Signal()
        with m.If(has_output | output_produce):
            m.d.comb += self.output.valid.eq(1)
        m.d.sync += has_output.eq(has_output + output_produce - output_transaction > 0)

        m.d.comb += self.input.ready.eq(self.output.ready | (~has_output & ~output_produce))

        return m
