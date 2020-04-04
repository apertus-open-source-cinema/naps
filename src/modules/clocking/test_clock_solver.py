from unittest import TestCase

import modules.clocking.clock_solver as solver
from modules.clocking.clocking_ressource import ClockingResource
from modules.clocking.term_builder import Var, Const, op
from numpy import arange


class TestClockingResource(ClockingResource):
    def __init__(self, input_freq):
        self.input_freq = Const(input_freq)
        self.vco_m = Var(iterator=range(1, 128), name="vco_m")
        self.vco_d = Var(iterator=range(1, 128), name="vco_d")
        self.output_d = [Var(iterator=range(1, 128), name="output_d_{}".format(x)) for x in range(8)]

    def topology(self):
        return [self.input_freq * self.vco_m / self.vco_d / out_d for out_d in self.output_d]

    def validity_constraints(self):
        return {
            (self.input_freq * self.vco_m / self.vco_d) < 1200e6,
            (self.input_freq * self.vco_m / self.vco_d) > 600e6,
        }


class TestClockSolver(TestCase):
    def test_get_common_variables(self):
        cr = TestClockingResource(100e6)
        self.assertEqual(
            solver.variables_for_constraints(
                solver.dispatch_constraints(
                    {*cr.topology(), *cr.validity_constraints()}, {}
                )
            ),
            {cr.vco_d, cr.vco_m}
        )

    def test_constraints_for_variables(self):
        cr = TestClockingResource(Const(100e6))
        self.assertEqual(repr(solver.constraints_for_variables(cr.validity_constraints(), {cr.vco_m, cr.vco_d})),
                         repr(cr.validity_constraints()))

    def test_valid_common_variable_configurations(self):
        cr = TestClockingResource(100e6)
        vcc = solver.valid_variable_configurations(cr.validity_constraints(), {})
        print(vcc.__next__())
        print(len(list(vcc)))

    def test_optimal_configuration(self):
        cr = TestClockingResource(100e6)
        port_a, port_b, port_c, *_ = cr.topology()
        constraints = [
            op.pow(port_a - 100e6, 2),
            port_a < 50e6,
            port_b == port_a / 2,
            port_c == port_a + port_b
        ]
        solver.solve_minlp({*cr.validity_constraints(), *constraints})
