import unittest

from amaranth import *
from amaranth.sim import Passive
from amaranth.lib.memory import Memory

from naps import SimPlatform, PacketizedStream, write_to_stream, read_from_stream, verify_stream_output_contract, LegalStreamSource
from naps.cores.stream.stream_memory import StreamMemoryReader


class StreamMemoryTest(unittest.TestCase):
    def test_hello_world(self):
        platform = SimPlatform()
        m = Module()

        address_stream = PacketizedStream(8)
        mem = Memory(shape=32, depth=128, init=[i + 2 for i in range(128)])
        reader = m.submodules.reader = StreamMemoryReader(address_stream, mem)
        m.submodules.memory = mem

        def write_process():
            for i in range(128):
                yield from write_to_stream(address_stream, payload=i, last=(i % 8) == 0)
            yield Passive()

        def read_process():
            for i in range(128):
                data, last = (yield from read_from_stream(reader.output, extract=("payload", "last")))
                assert data == i + 2
                assert last == ((i % 8) == 0)
            yield Passive()

        platform.add_sim_clock("sync", 100e6)
        platform.add_process(write_process, "sync")
        platform.sim(m, read_process)

    def test_output_stream_contract(self):
        def dut():
            input_stream = PacketizedStream(8)
            mem = Memory(shape=32, depth=128, init=[i + 2 for i in range(128)])
            dut = StreamMemoryReader(input_stream, mem)
            return (dut, dut.output, [LegalStreamSource(input_stream), mem])

        verify_stream_output_contract(dut)