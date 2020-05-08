from nmigen import *
from nmigen.test.utils import FHDLTestCase

from modules.hdmi.hdmi import TimingGenerator
from util.nmigen import get_signals
from util.sim import sim


class TestAxiSlave(FHDLTestCase):
    def test_axil_reg(self):
        dut = TimingGenerator(640, 480, 60)

        def testbench():
            last_x = 0
            for i in range(800):
                yield
                this_x = (yield dut.x)
                assert this_x == last_x + 1, "x increment failed"
                last_x = this_x
            yield
            assert 1 == (yield dut.y), "y increment failed"

        sim(dut, testbench, filename="hdmi", traces=get_signals(dut))
