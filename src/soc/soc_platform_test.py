import unittest

from soc.soc_platform import SocPlatform
from util.sim import SimPlatform


class ConcreteSocPlatform(SocPlatform):
    pass

class TestSocPlatform(unittest.TestCase):
    def test_is_instance(self):
        platform = ConcreteSocPlatform(SimPlatform())
        self.assertIsInstance(platform, SimPlatform)
