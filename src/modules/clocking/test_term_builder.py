import unittest

from modules.clocking.term_builder import Var, op, Op


class TestTermBuilder(unittest.TestCase):
    def test_basic(self):
        a = Var(range(0, 1))
        self.assertEqual(a.get_vars(), {a})

    def test_var_repr(self):
        a = Var(range(0, 1))
        self.assertEqual(repr(a), "<Var a range(0, 1)>")

    def test_op_repr(self):
        op = Op(first_operand="a", operation="__mul__", other_operands=["b", "c"])
        self.assertEqual(repr(op), "<Op  'a'.__mul__('b', 'c')>")

    def test_multiplication(self):
        a = Var(range(0, 1))
        b = Var(range(0, 1))
        self.assertEqual((a * b).get_vars(), {a, b})

    def test_op_builder(self):
        self.assertEqual(op.round(1), Op(operation=round, first_operand=None, other_operands=[(1)]))

    def test_eval(self):
        a = Var(range(0, 10))
        self.assertEqual(a.eval(a=1), 1)

        b = Var(range(0, 10))
        self.assertEqual((a * b).eval(a=4, b=3), 12)
        self.assertEqual((a * b * b).eval(a=10, b=2), 40)
        self.assertEqual((a / 10 * b).eval(a=10, b=2), 2)
        self.assertEqual(op.round(10 / 3).eval(), 3)

    def test_get_vars(self):
        a = Var(range(0, 10))
        b = Var(range(0, 10))
        c = Var(range(0, 10))
        self.assertEqual((a * (b * c)).get_vars(), {a, b, c})
        self.assertEqual((a * b * c).get_vars(), {a, b, c})
