import unittest
from nmigen import *
from naps import SimPlatform, Process, process_delay, do_nothing


class TestProcess(unittest.TestCase):
    def test_basic(self):
        platform = SimPlatform()
        m = Module()

        stage1 = Signal()
        stage2 = Signal()
        stage3 = Signal()
        end = Signal()
        stage3_barrier = Signal()
        with m.FSM():
            with Process(m, "INITIAL", to="END") as p:
                m.d.comb += stage1.eq(1)
                p += process_delay(m, 10)
                m.d.comb += stage2.eq(1)
                p += m.If(stage3_barrier)
                m.d.comb += stage3.eq(1)  # this will be ignored because we jump directly to the END state
            with m.State("END"):
                m.d.comb += end.eq(1)

        def testbench():
            self.assertEqual(1, (yield stage1))
            yield from do_nothing(10)
            self.assertEqual(0, (yield stage1))
            self.assertEqual(1, (yield stage2))
            yield stage3_barrier.eq(1)
            yield
            yield
            self.assertEqual(1, (yield end))



        platform.add_sim_clock("sync", 100e6)
        platform.sim(m, testbench)
