import unittest

from nmigen import *

from lib.bus.axi.sim_util import axil_read, axil_write
from lib.io.hdmi.cvt_python import generate_modeline
from lib.io.hdmi.hdmi import Hdmi
from soc.platforms import ZynqSocPlatform
from util.sim import SimPlatform


class SocSmokeTest(unittest.TestCase):
    def test_hdmi_registers(self, testdata=0x1):
        platform = ZynqSocPlatform(SimPlatform())

        class Pins:
            def __init__(self):
                self.r = Signal()
                self.g = Signal()
                self.b = Signal()
                self.clock = Signal()

        dut = Hdmi(Pins(), generate_clocks=False, modeline=generate_modeline(640, 480, 60))

        platform.add_sim_clock("pix", 117.5e6)

        def testbench():
            axi = platform.axi_lite_master
            memorymap = platform.memorymap
            for name, addr in memorymap.flattened.items():
                print(name, addr)
                yield from axil_read(axi, addr.address)
                # yield from axil_write(axi, addr.address, testdata)  # this will return an error if the register in question is a StatusRegister
                # self.assertEqual(testdata, (yield from axil_read(axi, addr.address)))

        platform.sim(dut, (testbench, "axi_lite"))
