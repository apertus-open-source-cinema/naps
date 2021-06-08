import unittest
from nmigen import *
from .packed_struct import packed_struct


@packed_struct
class DummyStruct:
    a: unsigned(1)
    b: unsigned(1)
    c: unsigned(2)


class PackedStructTest(unittest.TestCase):
    def test_non_nmigen(self):
        ts = DummyStruct(0b0101)
        assert ts.a == 1
        assert ts.b == 0
        assert ts.c == 0b01

        assert ts.fields() == ['a', 'b', 'c'], ts.fields()
