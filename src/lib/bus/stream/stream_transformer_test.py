import unittest

from nmigen import *

from lib.bus.stream.formal_util import LegalStreamSource, verify_stream_output_contract
from lib.bus.stream.stream import BasicStream
from lib.bus.stream.stream_transformer import StreamTransformer


class DemoStreamTransformerCore(Elaboratable):
    def __init__(self, input: BasicStream):
        self.input = input
        self.output = input.clone()

    def elaborate(self, platform):
        m = Module()

        with StreamTransformer(self.input, self.output, m):
            pass
        m.d.comb += self.output.payload.eq(self.input.payload + 1)

        return m


class StreamTransformerTest(unittest.TestCase):
    def test_stream_transformer_output_contracct(self):
        input_stream = BasicStream(32)
        verify_stream_output_contract(DemoStreamTransformerCore(input_stream), support_modules=(LegalStreamSource(input_stream),))
