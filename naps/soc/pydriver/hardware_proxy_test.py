import unittest
from naps.soc.pydriver.hardware_proxy import BitwiseAccessibleInteger


class BitwiseAccessibleIntegerTest(unittest.TestCase):
    def test_destruct(self):
        v = BitwiseAccessibleInteger(0b10100100)
        self.assertEqual(v[0], 0)
        self.assertEqual(v[2], 1)
        self.assertEqual(v[4:8], 0b1010)

    def test_construct(self):
        v = BitwiseAccessibleInteger(256)
        v[0] = 1
        self.assertEqual(int(v), 257)

        v = BitwiseAccessibleInteger()
        v[8] = 1
        self.assertEqual(int(v), 256)

        v = BitwiseAccessibleInteger(0b00001111)
        v[0:4] = 0
        self.assertEqual(int(v), 0)

        v = BitwiseAccessibleInteger(0b01011111)
        v[4:8] = 0b1010
        self.assertEqual(int(v), 0b10101111)