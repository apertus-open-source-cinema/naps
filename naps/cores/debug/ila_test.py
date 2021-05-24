import unittest

from nmigen import *
from naps import SimPlatform, do_nothing, SimSocPlatform, StatusSignal, probe, trigger, add_ila


class IlaTest(unittest.TestCase):
    def test_with_driver(self):
        platform = SimSocPlatform(SimPlatform())

        class Top(Elaboratable):
            def __init__(self):
                self.up_counter = StatusSignal(16)
                self.down_counter = StatusSignal(16, reset=1000)

            def elaborate(self, platform):
                m = Module()
                m.d.sync += self.up_counter.eq(self.up_counter + 1)
                m.d.sync += self.down_counter.eq(self.down_counter - 1)

                add_ila(platform, trace_length=100)
                probe(m, self.up_counter)
                probe(m, self.down_counter)
                trigger(m, self.up_counter > 200)
                return m

        def driver(design):
            design.ila.arm()
            yield from do_nothing(1000)
            ila_trace = list(design.ila.get_values())
            last_up = 150
            last_down = 1000 - 150
            assert len(ila_trace) == 100
            for up, down in ila_trace:
                assert up == last_up + 1, (up, last_up)
                last_up = up
                assert down == last_down - 1, (down, last_down)
                last_down = down
        platform.add_driver(driver)

        platform.add_sim_clock('sync', 10e6)
        platform.sim(Top())
