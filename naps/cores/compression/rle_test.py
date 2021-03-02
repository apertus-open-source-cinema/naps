import unittest
from nmigen import *
from naps import SimPlatform
from naps.stream import PacketizedStream, verify_stream_output_contract, LegalStreamSource, write_to_stream, read_from_stream
from . import ZeroRleEncoder, RleEncodingSpace


class RleTest(unittest.TestCase):
    def test_basic(self):
        platform = SimPlatform()
        m = Module()

        input = PacketizedStream(8)
        input_data = [1, 0, 1, *([0] * 14), 1]
        run_length_options = [3, 10, 27, 80, 160]

        rle = m.submodules.rle = ZeroRleEncoder(input, RleEncodingSpace(range(0, 255), run_length_options, zero_value=0))

        def write_process():
            for x in input_data:
                yield from write_to_stream(input, payload=x)

        def read_process():
            received = []
            while True:
                try:
                    received.append((yield from read_from_stream(rle.output)))
                except TimeoutError:
                    break
            decoded = []
            for x in received:
                if x < 256:
                    decoded.append(x)
                else:
                    decoded += ([0] * run_length_options[x - 256])
            self.assertEquals(input_data, decoded)

        platform.add_sim_clock("sync", 100e6)
        platform.add_process(write_process, "sync")
        platform.sim(m, read_process)

    def test_output_stream_properties(self):
        input = PacketizedStream(8)
        encoding_space = RleEncodingSpace(range(0, 255), [3, 10, 27, 80, 160], zero_value=0)
        verify_stream_output_contract(ZeroRleEncoder(input, encoding_space), support_modules=(LegalStreamSource(input),))
