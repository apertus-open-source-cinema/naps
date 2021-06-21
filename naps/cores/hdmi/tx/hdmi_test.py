import unittest
from nmigen.build import Clock
from naps import SimPlatform
from .. import generate_modeline, parse_modeline
from . import HdmiClocking, HdmiTimingGenerator


class TestHdmi(unittest.TestCase):
    def test_timing_generator(self):
        platform = SimPlatform()
        dut = HdmiTimingGenerator(parse_modeline(generate_modeline(640, 480, 60)))

        def testbench():
            last_x = 0
            for i in range(800 - 1):
                yield
                this_x = (yield dut.x)
                assert this_x == last_x + 1, "x increment failed"
                last_x = this_x
            yield
            assert 1 == (yield dut.y), "y increment failed"

        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut, testbench)

    def test_mmcm_calculation(self):
        clocking = HdmiClocking(Clock(79.75e6), pix_domain="pix")
        clocking.find_valid_config()
