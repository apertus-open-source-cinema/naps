import random
import unittest

from naps.cores.stream.buffer import StreamBuffer
from naps.stream.formal_util import verify_stream_output_contract
from naps.stream.sim_util import write_to_stream, read_from_stream
from naps.stream import BasicStream
from naps.util.sim import SimPlatform


class TestBuffer(unittest.TestCase):
    def test_basic(self):
        platform = SimPlatform()
        input_stream = BasicStream(32)
        dut = StreamBuffer(input_stream)

        random.seed(0)
        test_data = [random.randrange(0, 2**32) for _ in range(100)]

        def write_process():
            for d in test_data:
                yield from write_to_stream(input_stream, payload=d)
        platform.add_process(write_process, "sync")

        def read_process():
            for expected in test_data:
                read = yield from read_from_stream(dut.output)
                self.assertEquals(read, expected)
        platform.add_process(read_process, "sync")

        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut)

    def test_output_properties(self):
        input = BasicStream(32)
        # important: we prove here that ANY input produces a contract obeying output
        verify_stream_output_contract(StreamBuffer(input))
