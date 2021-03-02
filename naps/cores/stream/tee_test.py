import unittest
from naps.stream import PacketizedStream, LegalStreamSource, verify_stream_output_contract
from .tee import StreamTee, StreamCombiner


class StreamTeeTest(unittest.TestCase):
    def test_tee_output_stream_contract(self):
        input_stream = PacketizedStream(32)
        dut = StreamTee(input_stream)
        output1, output2 = dut.get_output(), dut.get_output()
        verify_stream_output_contract(dut, stream_output=output1, support_modules=(LegalStreamSource(input_stream),))
        verify_stream_output_contract(dut, stream_output=output2, support_modules=(LegalStreamSource(input_stream),))

    def test_stream_combiner_output_stream_contract(self):
        input1, input2 = PacketizedStream(32), PacketizedStream(32)
        dut = StreamCombiner(input1, input2, merge_payload=True)
        verify_stream_output_contract(dut, support_modules=(LegalStreamSource(input1), LegalStreamSource(input2)))
