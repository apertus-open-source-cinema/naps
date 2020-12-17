import unittest
from nmigen import *
from lib.bus.stream.sim_util import write_to_stream, read_from_stream
from lib.bus.stream.stream import BasicStream
from lib.compression.rle import ZeroRle
from util.sim import SimPlatform


class RleTest(unittest.TestCase):
    def test_basic(self):
        platform = SimPlatform()
        m = Module()

        input = BasicStream(8)
        input_data = [1, 0, 1, *([0] * 14), 1]
        run_length_options = [3, 10, 27, 80, 160]

        rle = m.submodules.rle = ZeroRle(input, run_length_options)

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
