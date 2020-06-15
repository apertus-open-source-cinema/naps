import unittest
from os.path import dirname, join

from nmigen import Signal

from cores.hispi.hispi import ControlSequenceDecoder
from util.sim import SimPlatform


class TestHispi(unittest.TestCase):
    def test_hispi_control_sequence_decoder(self, filename="test_data.txt"):
        platform = SimPlatform()
        input_data = Signal(12)
        dut = ControlSequenceDecoder(input_data)

        def testbench():
            with open(join(dirname(__file__), filename)) as f:
                lines = f.readlines()

            def lane_n_generator(n):
                for line in lines:
                    for i in [i * 4 + n for i in range(6)]:
                        yield "1" if line[i] == "0" else "0"

            generator = lane_n_generator(2)
            for i in range(100000):
                if (yield dut.do_bitslip):
                    next(generator)
                word = int("".join(next(generator) for _ in range(12)), 2)
                yield input_data.eq(word)
                yield



        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut, testbench)
