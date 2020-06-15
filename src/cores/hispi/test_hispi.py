import unittest
from os.path import dirname, join
import lzma

from nmigen import Signal

from cores.hispi.hispi import ControlSequenceDecoder
from util.sim import SimPlatform


class TestHispi(unittest.TestCase):
    def test_hispi_control_sequence_decoder(self):
        platform = SimPlatform()
        input_data = Signal(12)
        dut = ControlSequenceDecoder(input_data)

        def testbench():
            with lzma.open(join(dirname(__file__), "test_data.txt.gz")) as f:
                def lane_n_generator(n):
                    while True:
                        line = f.readline()
                        for i in reversed([i * 4 + n for i in range(6)]):
                            val = "1" if line[i] == b"0" else "0"
                            yield val

                generator = lane_n_generator(0)
                for i in range(100000):
                    if (yield dut.do_bitslip):
                        next(generator)
                    word = int("".join(next(generator) for _ in range(12)), 2)
                    yield input_data.eq(word)
                    yield
                assert (yield dut.data_valid) == 1

        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut, testbench)
