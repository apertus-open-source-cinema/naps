from nmigen import *
from nmigen.back.pysim import Simulator
from nmigen.test.utils import FHDLTestCase
from tqdm import tqdm

from modules.hdmi.hdmi import TimingGenerator, Hdmi
from soc.SimPlatform import SimPlatform
from soc.zynq.ZynqSocPlatform import ZynqSocPlatform
from util.bundle import Bundle
from util.cvt import generate_modeline, parse_modeline
from util.nmigen import get_signals


class TestHdmi(FHDLTestCase):
    def test_timing_generator(self):
        platform = SimPlatform()
        dut = TimingGenerator(parse_modeline(generate_modeline(1920, 1080, 30)))

        def testbench():
            last_x = 0
            for i in range(1920 * 1080 * 100):
                yield
                this_x = (yield dut.x)
                # assert this_x == last_x + 1, "x increment failed"
                last_x = this_x
            yield
            assert 1 == (yield dut.y), "y increment failed"

        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut, (testbench, "sync"), traces=get_signals(dut))

test = TestHdmi()
test.test_timing_generator()
