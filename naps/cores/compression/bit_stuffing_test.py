import unittest
from nmigen import *

from naps.stream.formal_util import verify_stream_output_contract, LegalStreamSource
from naps.stream.sim_util import write_to_stream, read_from_stream
from naps.cores.compression.bit_stuffing import BitStuffer, VariableWidthStream
from naps.util.sim import SimPlatform


class BitStufferTest(unittest.TestCase):
    def test_basic(self):
        platform = SimPlatform()
        m = Module()

        input_data = ['00000001', '00000011', '00000111', '00001111']

        input = VariableWidthStream(32)
        bit_stuffer = m.submodules.bit_stuffer = BitStuffer(input, 32)

        def write_process():
            for word in input_data:
                yield from write_to_stream(input, payload=int(word, 2), current_width=len(word))

        def read_process():
            read = "{:032b}".format((yield from read_from_stream(bit_stuffer.output)))
            print(read)
            self.assertEquals(read, "".join(reversed(input_data)))

        platform.add_sim_clock("sync", 100e6)
        platform.add_process(write_process, "sync")
        platform.sim(m, read_process)

    def test_advanced(self):
        platform = SimPlatform()
        m = Module()

        input_data = ['1110010', '1101001', '1111101', '1111101', '000110', '11010111000101', '0100111110010011', '011100', '000110', '001110', '1111101', '1100101', '0100111110010011',
                      '111111101101', '111111101111111']

        input = VariableWidthStream(32)
        bit_stuffer = m.submodules.bit_stuffer = BitStuffer(input, 32)

        def write_process():
            for word in input_data:
                yield from write_to_stream(input, payload=int(word, 2), current_width=len(word))

        def read_process():
            read = []
            while True:
                try:
                    read.append("{:032b}".format((yield from read_from_stream(bit_stuffer.output))))
                except TimeoutError:
                    break
            read_bitstring = "".join("".join(reversed(x)) for x in read)
            print(read_bitstring)
            input_bitstring = "".join("".join(reversed(x)) for x in input_data)
            print(input_bitstring)
            print(read_bitstring)
            self.assertTrue(input_bitstring.startswith(read_bitstring))

        platform.add_sim_clock("sync", 100e6)
        platform.add_process(write_process, "sync")
        platform.sim(m, read_process)

    def test_advanced_last(self):
        platform = SimPlatform()
        m = Module()

        input_data = ['1110010', '1101001', '1111101', '1111101', '000110', '11010111000101', '0100111110010011', '011100', '000110', '001110', '1111101', '1100101', '0100111110010011',
                      '111111101101', '111111101111111']

        input = VariableWidthStream(32)
        bit_stuffer = m.submodules.bit_stuffer = BitStuffer(input, 32)

        def write_process():
            for i, word in enumerate(input_data):
                yield from write_to_stream(input, payload=int(word, 2), current_width=len(word), last=(i == len(input_data) - 1))

        def read_process():
            read = []
            for i in range(100):
                v, last = (yield from read_from_stream(bit_stuffer.output, extract=("payload", "last")))
                read.append("{:032b}".format(v))
                if last:
                    break
            assert i != 99, "timeout"
            read_bitstring = "".join("".join(reversed(x)) for x in read)
            print(read_bitstring)
            input_bitstring = "".join("".join(reversed(x)) for x in input_data)
            print(input_bitstring)
            print(read_bitstring)
            self.assertTrue(read_bitstring.startswith(input_bitstring))

        platform.add_sim_clock("sync", 100e6)
        platform.add_process(write_process, "sync")
        platform.sim(m, read_process)

    def test_output_stream_properties(self):
        input = VariableWidthStream(32)
        verify_stream_output_contract(BitStuffer(input, 32), support_modules=(LegalStreamSource(input),))
