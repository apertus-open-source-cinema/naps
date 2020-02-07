from unittest import TestCase

import modules.clocking.clock_solver as solver
from modules.clocking.clocking_ressource import ClockingResource
from modules.clocking.term_builder import Var, Const
from numpy import arange


class TestClockingResource(ClockingResource):
    def __init__(self, input_freq):
        self.input_freq = input_freq
        self.vco_m = Var(range(1, 128), name="vco_m")
        self.vco_d = Var(arange(1, 128, 0.25), name="vco_d")
        self.output_d = [Var(range(1, 128), name="output_d_{}".format(x)) for x in range(8)]

    def topology(self):
        return [self.input_freq * self.vco_m / self.vco_d / out_d for out_d in self.output_d]

    def validity_constraints(self):
        return {
            (self.input_freq * self.vco_m / self.vco_d) < 1200e6,
            (self.input_freq * self.vco_m / self.vco_d) > 600e6,
        }


class TestClockSolver(TestCase):
    def test_get_common_variables(self):
        cr = TestClockingResource(Const(100e6))
        self.assertEqual(solver.common_variables(cr), {cr.vco_d, cr.vco_m})

    def test_cosnstraints_for_variables(self):
        cr = TestClockingResource(Const(100e6))
        self.assertEqual(repr(solver.constraints_for_variables(cr.validity_constraints(), {cr.vco_m, cr.vco_d})),
                         repr(cr.validity_constraints()))

    def test_valid_common_variable_configurations(self):
        cr = TestClockingResource(Const(100e6))
        vcc = solver.valid_common_variable_configurations(cr)
        print(vcc.__next__())
        print(len(list(vcc)))