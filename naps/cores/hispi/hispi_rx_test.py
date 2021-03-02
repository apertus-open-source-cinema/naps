import lzma
import unittest
from os.path import dirname, join
from nmigen import Signal
from naps import SimPlatform
from .hispi_rx import LaneManager


class FakeSensorResource:
    def __init__(self):
        self.lvds = Signal(4)
        self.lvds_clk = Signal()


class TestHispi(unittest.TestCase):
    def check_hispi_lane_manager(self, datafile):
        platform = SimPlatform()
        input_data = Signal(12)
        dut = LaneManager(input_data)

        def testbench():
            def lane_n_generator(n):
                with lzma.open(join(dirname(__file__), datafile), "r") as f:
                    for line in f:
                        line = line.replace(b" ", b"")
                        for i in range(12):
                            val = "0" if line[i + (n * 12)] == ord("0") else "1"
                            yield val

            generator = lane_n_generator(0)
            last_valid = 0
            line_ctr = 0
            for i in range(200000):
                try:
                    if (yield dut.do_bitslip):
                        next(generator)
                    word = int("".join(reversed([next(generator) for _ in range(12)])),
                               2)  # TODO: figure out, how this reversed() affects the real world
                    yield input_data.eq(word)
                except RuntimeError:  # this is raised when we are done instead of StopIteration
                    break

                if (last_valid == 0) and ((yield dut.output.valid) == 1):
                    last_valid = 1
                    line_ctr = 0
                elif (last_valid == 1) and ((yield dut.output.valid) == 1):
                    line_ctr += 1
                elif (last_valid == 1) and ((yield dut.output.valid) == 0):
                    last_valid = 0
                    assert (line_ctr + 1) * 4 == 2304

                yield
            assert (yield dut.is_aligned) == 1, "dut is not aligned"

        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut, testbench)

    def test_hispi_lane_manager_old_data(self):
        self.check_hispi_lane_manager("test_data_old.txt.lzma")

    def test_hispi_lane_manager_new_data(self):
        self.check_hispi_lane_manager("test_data_new.txt.lzma")