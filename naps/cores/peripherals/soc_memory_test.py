import unittest

from naps import SimPlatform, SocMemory, axil_read, axil_write, do_nothing, SimSocPlatform
from naps.soc.platform.zynq import ZynqSocPlatform


class SocMemoryTest(unittest.TestCase):
    def test_smoke(self):
        platform = ZynqSocPlatform(SimPlatform())

        dut = SocMemory(width=32, depth=128)

        def testbench():
            axi = platform.axi_lite_master
            memorymap = platform.memorymap
            for addr in range(128):
                yield from axil_write(axi, 4*addr + 0x40000000, addr)
            for addr in range(128):
                self.assertEqual(addr, (yield from axil_read(axi, 4*addr + 0x40000000)))

        platform.sim(dut, (testbench, "axi_lite"))

    def test_with_driver(self):
        platform = SimSocPlatform(SimPlatform())

        dut = SocMemory(width=64, depth=128)

        def driver(design):
            for i in range(128):
                design[i] = i * i << 30
                yield from do_nothing(10)
            for i in reversed(range(128)):
                self.assertEqual(design[i], i * i << 30)
                yield from do_nothing(10)
        platform.add_driver(driver)

        platform.sim(dut)
