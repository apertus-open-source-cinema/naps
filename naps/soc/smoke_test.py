import unittest
from nmigen import *
from naps import ZynqSocPlatform, SimPlatform
from naps.cores.axi import axil_read
from naps.cores.hdmi import generate_modeline, HdmiTx
from naps.soc.pydriver.driver_items import DriverItem


class SocSmokeTest(unittest.TestCase):
    def test_hdmi_registers(self, testdata=0x1):
        platform = ZynqSocPlatform(SimPlatform())

        class Pins:
            def __init__(self):
                self.r = Signal()
                self.g = Signal()
                self.b = Signal()
                self.clock = Signal()

        dut = HdmiTx(Pins(), generate_clocks=False, modeline=generate_modeline(640, 480, 60))

        platform.add_sim_clock("pix", 117.5e6)

        def testbench():
            axi = platform.axi_lite_master
            memorymap = platform.memorymap
            for name, addr in memorymap.flattened.items():
                if not isinstance(addr, DriverItem):
                    yield from axil_read(axi, addr.address)

        platform.sim(dut, (testbench, "axi_lite"))
