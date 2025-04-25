import unittest

from naps import SimPlatform, SocMemory, axil_read, axil_write, do_nothing, SimSocPlatform
from naps.soc.platform.zynq import ZynqSocPlatform


class SocMemoryTest(unittest.TestCase):
    def test_smoke(self):
        platform = ZynqSocPlatform(SimPlatform())
        memory_depth = 128
        dut = SocMemory(shape=32, init=[], depth=memory_depth)

        def testbench():
            axi = platform.axi_lite_master
            memorymap = platform.memorymap
            for addr in range(memory_depth):
                yield from axil_write(axi, 4*addr + 0x40000000, addr)
            for addr in range(memory_depth):
                self.assertEqual(addr, (yield from axil_read(axi, 4*addr + 0x40000000)))

        platform.sim(dut, (testbench, "axi_lite"))

    def test_with_driver(self):
        platform = SimSocPlatform(SimPlatform())

        memory_depth = 128
        dut = SocMemory(shape=64, depth=memory_depth, init=[])

        def driver(design):
            for i in range(memory_depth):
                design[i] = i * i << 30
                yield from do_nothing(10)
            for i in reversed(range(memory_depth)):
                self.assertEqual(design[i], i * i << 30)
                yield from do_nothing(10)
        platform.add_driver(driver)

        platform.sim(dut)


    def test_with_driver_simple(self):
        platform = SimSocPlatform(SimPlatform())

        memory_depth = 2
        dut = SocMemory(shape=32, depth=memory_depth, init=[])

        def driver(design):
            for i in range(memory_depth):
                design[i] = i
                yield from do_nothing(10)
            for i in reversed(range(memory_depth)):
                self.assertEqual(design[i], i)
                yield from do_nothing(10)
        platform.add_driver(driver)

        platform.sim(dut)
