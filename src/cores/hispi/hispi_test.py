import unittest
from tqdm import tqdm
from os.path import dirname, join
import lzma

from nmigen import Signal

from cores.hispi.hispi import LaneManager
from util.sim import SimPlatform


class TestHispi(unittest.TestCase):
    def test_hispi_lane_manager(self):
        platform = SimPlatform()
        input_data = Signal(12)
        dut = LaneManager(input_data)

        def testbench():
            with lzma.open(join(dirname(__file__), "test_data.txt.lzma"), "r") as f:
                def lane_n_generator(n):
                    for line in f:
                        # line = f.readline()
                        for i in reversed([i * 4 + n for i in range(6)]):
                            val = "1" if line[i] == ord("0") else "0"
                            yield val

                generator = lane_n_generator(0)
                last_valid = 0
                line_ctr = 0
                for i in tqdm(range(10000000)):
                    if (yield dut.do_bitslip):
                        next(generator)
                    word = int("".join(next(generator) for _ in range(12)), 2)
                    yield input_data.eq(word)

                    if (last_valid == 0) and ((yield dut.output.valid) == 1):
                        last_valid = 1
                        line_ctr = 0
                    elif (last_valid == 1) and ((yield dut.output.valid) == 1):
                        line_ctr += 1
                    elif (last_valid == 1) and ((yield dut.output.valid) == 0):
                        last_valid = 0
                        assert (line_ctr + 1) * 4 == 2304

                    yield
                assert (yield dut.is_aligned) == 1

        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut, testbench)
