import unittest

from soc.soc_platform import SocPlatform
from util.sim import SimPlatform


class ConcreteSocPlatform(SocPlatform):
    def BusSlave(self, handle_read, handle_write, memorymap):
        pass


class TestSocPlatform(unittest.TestCase):
    def test_is_instance(self):
        platform = ConcreteSocPlatform(SimPlatform())
        self.assertIsInstance(platform, SimPlatform)
