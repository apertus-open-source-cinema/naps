import unittest

from naps import SimPlatform, SocMemory, axil_read, axil_write
from naps.soc.platform.zynq import ZynqSocPlatform


class SocMemoryTest(unittest.TestCase):
    def test_smoke(self):
        platform = ZynqSocPlatform(SimPlatform())

        dut = SocMemory(width=32, depth=128)

        def testbench():
            axi = platform.axi_lite_master
            memorymap = platform.memorymap
            for addr in range(128):
                yield from axil_write(axi, addr + 0x40000000, addr)
                self.assertEqual(addr, (yield from axil_read(axi, addr + 0x40000000)))

        platform.sim(dut, (testbench, "axi_lite"))