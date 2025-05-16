import unittest

from amaranth import *
from amaranth.lib import wiring
from amaranth.sim import Passive
from amaranth.lib.memory import Memory

from naps import SimPlatform, write_to_stream, read_from_stream, verify_stream_output_contract, LegalStreamSource, \
    Packet
from naps.cores.stream.stream_memory import StreamMemoryReader
from naps.stream.formal_util import stream_contract_test


class StreamMemoryTest(unittest.TestCase):
    def test_hello_world(self):
        platform = SimPlatform()
        m = Module()

        mem = Memory(shape=32, depth=128, init=[i + 2 for i in range(128)])
        reader = m.submodules.reader = StreamMemoryReader(mem, address_shape=Packet(7))
        m.submodules.mem = mem

        def write_process():
            for i in range(128):
                yield from write_to_stream(reader.input, reader.input.p.shape().const({"p": i, "last": (i % 8) == 0}))
            yield Passive()

        def read_process():
            for i in range(128):
                yield from read_from_stream(reader.output)
                data = yield reader.output.p.p
                last = yield reader.output.p.last
                assert data == i + 2
                assert last == ((i % 8) == 0)
            yield Passive()

        platform.add_sim_clock("sync", 100e6)
        platform.add_process(write_process, "sync")
        platform.sim(m, read_process)

    @stream_contract_test
    def test_output_stream_contract(self, plat, m):
        mem = Memory(shape=32, depth=128, init=[i + 2 for i in range(128)])
        m.submodules.reader = reader = StreamMemoryReader(mem)
        wiring.connect(m, reader.input, plat.request_port(reader.input))
        return reader.output
