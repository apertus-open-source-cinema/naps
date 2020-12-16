import unittest
from nmigen import *
from lib.bus.stream.sim_util import write_to_stream, read_from_stream
from lib.bus.stream.stream import BasicStream
from lib.compression.bit_stuffing import BitStuffer
from lib.compression.huffman_encoder import HuffmanEncoder
from util.sim import SimPlatform
from bitarray import bitarray


class HuffmanTest(unittest.TestCase):
    def test_hello_world(self):
        platform = SimPlatform()
        m = Module()

        input = BasicStream(8)
        input_data = "hello, world :)"

        huffman = m.submodules.huffman = HuffmanEncoder(input)

        def write_process():
            for c in input_data:
                yield from write_to_stream(input, payload=ord(c))

        def read_process():
            read = ""
            while True:
                try:
                    data, length = (yield from read_from_stream(huffman.output, extract=("payload", "current_width")))
                    bitstring = "{:0255b}".format(data)[::-1][:length]
                    print(bitstring)
                    read += bitstring
                except TimeoutError:
                    break
            print(read)
            decode_iter = bitarray(read).iterdecode({k: bitarray(v[::-1]) for k, v in huffman.table.items()})
            decoded = ""
            try:
                for c in decode_iter:
                    decoded += chr(c)
            except ValueError:  # Decoding may not finish with the byte boundary
                pass
            self.assertEquals(input_data, decoded)

        platform.add_sim_clock("sync", 100e6)
        platform.add_process(write_process, "sync")
        platform.sim(m, read_process)

    def test_hello_world_bit_stuffing(self):
        platform = SimPlatform()
        m = Module()

        input = BasicStream(8)
        input_data = "hello, world :)"

        huffman = m.submodules.huffman = HuffmanEncoder(input)
        bit_stuffing = m.submodules.bit_stuffing = BitStuffer(huffman.output, 8)

        def write_process():
            for c in input_data:
                yield from write_to_stream(input, payload=ord(c))

        def read_process():
            read = []
            while True:
                try:
                    payload = (yield from read_from_stream(bit_stuffing.output, extract=("payload")))
                    read.append("{:08b}".format(payload))
                except TimeoutError:
                    break
            read_bitarray = "".join(x[::-1] for x in read)
            print(read_bitarray)
            decode_iter = bitarray(read_bitarray).iterdecode({k: bitarray(v[::-1]) for k, v in huffman.table.items()})
            decoded = ""
            try:
                for c in decode_iter:
                    decoded += chr(c)
            except ValueError:  # Decoding may not finish with the byte boundary
                pass
            self.assertTrue(input_data.startswith(decoded))

        platform.add_sim_clock("sync", 100e6)
        platform.add_process(write_process, "sync")
        platform.sim(m, read_process)