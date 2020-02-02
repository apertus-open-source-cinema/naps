import unittest

from util.future_int import FutureInt, cache


class TestLazyInt(unittest.TestCase):
    def test_basic(self):
        a = FutureInt()
        self.assertEqual(a.be(3), 3)
        self.assertEqual(int(a * 10), 30)

    def test_not_fulfilled(self):
        a = FutureInt()
        with self.assertRaises(AssertionError):
            int(a)

    def test_be_li(self):
        a = FutureInt(3)
        b = FutureInt(a)
        self.assertEqual(int(b), int(a))

    def test_equality(self):
        a = FutureInt()
        self.assertEqual(a, a)
        self.assertEqual(a + 10, a + 10)

    def test_both_sides_li_equality(self):
        a = FutureInt(3)
        b = FutureInt(4)
        self.assertEqual(int(a + b), 7)

    def test_complex_equality(self):
        a = FutureInt()
        b = FutureInt(a)
        self.assertEqual(a, b)


class TestCache(unittest.TestCase):
    def test_present(self):
        c = []
        result = cache("a", lambda : 1, cache=c)
        self.assertEqual(result, 1)
        self.assertEqual(cache("a", lambda: 2, cache=c), 1)

    def test_not_present(self):
        c = []
        self.assertEqual(cache(1, lambda : 1, cache=c), 1)