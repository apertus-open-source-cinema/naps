import unittest
from naps import SimPlatform
from . import SocPlatform


class ConcreteSocPlatform(SocPlatform):
    pass


class TestSocPlatform(unittest.TestCase):
    def test_is_instance(self):
        platform = ConcreteSocPlatform(SimPlatform())
        self.assertIsInstance(platform, SimPlatform)
        self.assertIsInstance(platform, ConcreteSocPlatform)
        self.assertIsInstance(platform, SocPlatform)
