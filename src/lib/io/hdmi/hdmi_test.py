import unittest

from nmigen import *
from nmigen.build import Clock

from lib.io.hdmi.hdmi import TimingGenerator, Hdmi, HdmiClocking
from soc.platforms.zynq import ZynqSocPlatform
from lib.bus.axi.sim_util import axil_read, axil_write
from util.sim import SimPlatform
from lib.io.hdmi.parse_modeline import parse_modeline
from lib.io.hdmi.cvt_python import generate_modeline
from util.nmigen_misc import get_signals


class TestHdmi(unittest.TestCase):
    def test_timing_generator(self):
        platform = SimPlatform()
        dut = TimingGenerator(parse_modeline(generate_modeline(640, 480, 60)))

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
        platform.sim(dut, testbench, traces=get_signals(dut))

    def test_hdmi_registers(self, testdata=0x1):
        platform = ZynqSocPlatform(SimPlatform())

        class Pins:
            def __init__(self):
                self.data = Signal(3)
                self.clock = Signal()

        dut = Hdmi(Pins(), generate_clocks=False, modeline=generate_modeline(640, 480, 60))

        platform.add_sim_clock("pix", 117.5e6)

        def testbench():
            axi = platform.axi_lite_master
            memorymap = platform.memorymap
            for name, addr in memorymap.flattened.items():
                print(name, addr)
                yield from axil_read(axi, addr.address)
                yield from axil_write(axi, addr.address, testdata)
                # self.assertEqual(testdata, (yield from axil_read(axi, addr.address)))

        platform.sim(dut, (testbench, "axi_lite"))

    def test_mmcm_calculation(self):
        clocking = HdmiClocking(Clock(79.75e6))
        clocking.find_valid_config()
