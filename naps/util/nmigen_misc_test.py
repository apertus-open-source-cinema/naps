import unittest

from nmigen import *
from nmigen.sim import Simulator

from .nmigen_misc import nMin, nAny, nAll, nMax, assert_is_pot, log2, ends_with, nAbsDifference


class TestNMigenMisc(unittest.TestCase):
    def _resolve(self, expr):
        sim = Simulator(Module())

        a = []

        def testbench():
            a.append((yield expr))

        sim.add_process(testbench)
        sim.run()
        return a[0]

    def test_nMin(self):
        self.assertEqual(3, self._resolve(nMin(3, 7)))
        self.assertEqual(3, self._resolve(nMin(7, 3)))

    def test_nMax(self):
        self.assertEqual(7, self._resolve(nMax(3, 7)))
        self.assertEqual(7, self._resolve(nMax(7, 3)))

    def test_nAny(self):
        self.assertEqual(1, self._resolve(nAny([Const(1), Const(0), Const(0), Const(0)])))
        self.assertEqual(1, self._resolve(nAny([Const(0), Const(0), Const(1), Const(1)])))
        self.assertEqual(0, self._resolve(nAny([Const(0), Const(0), Const(0), Const(0)])))

    def test_nAll(self):
        self.assertEqual(1, self._resolve(nAll([Const(1), Const(1), Const(1), Const(1)])))
        self.assertEqual(0, self._resolve(nAll([Const(0), Const(0), Const(1), Const(1)])))
        self.assertEqual(0, self._resolve(nAll([Const(0), Const(0), Const(0), Const(0)])))

    def test_is_pot(self):
        assert_is_pot(2)
        assert_is_pot(4)
        assert_is_pot(64)
        assert_is_pot(512)
        with self.assertRaisesRegex(AssertionError, "is not a power of two"):
            assert_is_pot(7)
        with self.assertRaisesRegex(AssertionError, "is not a power of two"):
            assert_is_pot(42)
        with self.assertRaisesRegex(AssertionError, "is not a power of two"):
            assert_is_pot(196)

    def test_log2(self):
        self.assertEqual(1, log2(2))
        self.assertEqual(2, log2(4))
        self.assertEqual(10, log2(1024))
        with self.assertRaisesRegex(AssertionError, "is not a power of two"):
            assert_is_pot(196)

    def test_ends_with(self):
        self.assertTrue(self._resolve(ends_with(Const(0b0001, 4), "01")))
        self.assertFalse(self._resolve(ends_with(Const(0b0001, 4), "10")))
        self.assertTrue(self._resolve(ends_with(Const(0b10001011, 4), "1011")))
        self.assertTrue(self._resolve(ends_with(Const(0b10001011, 4), "011")))
        self.assertFalse(self._resolve(ends_with(Const(0b10001011, 4), "0110")))

    def test_nAbsDifference(self):
        self.assertEqual(7, self._resolve(nAbsDifference(10, 3)))
        self.assertEqual(7, self._resolve(nAbsDifference(3, 10)))
        self.assertEqual(3, self._resolve(nAbsDifference(12, 9)))
        self.assertEqual(3, self._resolve(nAbsDifference(9, 12)))
