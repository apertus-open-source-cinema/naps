import unittest

from nmigen import *
from naps import SimPlatform, do_nothing, SimSocPlatform, StatusSignal, probe, trigger, add_ila


class IlaTest(unittest.TestCase):
    def test_with_driver(self):
        platform = SimSocPlatform(SimPlatform())

        class Top(Elaboratable):
            def __init__(self):
                self.counter = StatusSignal(16)

            def elaborate(self, platform):
                m = Module()
                m.d.sync += self.counter.eq(self.counter + 1)

                add_ila(platform, trace_length=100)
                probe(m, self.counter)
                trigger(m, self.counter > 200)
                return m

        def driver(design):
            design.ila.arm()
            yield from do_nothing(1000)
            ila_trace = list(design.ila.get_values())
            last = 150
            assert len(ila_trace) == 100
            for x, in ila_trace:
                assert x == last + 1, (x, last)
                last = x
        platform.add_driver(driver)

        platform.add_sim_clock('sync', 10e6)
        platform.sim(Top())
