import random
import unittest

from amaranth.lib import wiring

from naps.cores.stream.buffer import StreamBuffer
from naps.stream.formal_util import stream_contract_test
from naps.stream.sim_util import write_to_stream, read_from_stream
from naps.util.sim import SimPlatform


class TestBuffer(unittest.TestCase):
    def test_basic(self):
        platform = SimPlatform()
        dut = StreamBuffer(32)

        random.seed(0)
        test_data = [random.randrange(0, 2**32) for _ in range(100)]

        def write_process():
            for d in test_data:
                yield from write_to_stream(dut.input, payload=d)
        platform.add_process(write_process, "sync")

        def read_process():
            for expected in test_data:
                read = yield from read_from_stream(dut.output)
                self.assertEqual(read, expected)
        platform.add_process(read_process, "sync")

        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut)

    @stream_contract_test
    def test_output_properties(self, plat, m):
        m.submodules.dut = dut = StreamBuffer(32)
        wiring.connect(m, buffer_input=dut.input, port=plat.request_port(dut.input))
        return dut.output
