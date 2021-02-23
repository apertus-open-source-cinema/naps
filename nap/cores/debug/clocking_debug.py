# reports the clock frequencies of the design using csr infrastructure

from nmigen import *
from nap import StatusSignal, driver_property

__all__ = ["ClockingDebug", "ClockDebug"]


class ClockingDebug(Elaboratable):
    def __init__(self, *args):
        self.clockdomains = args

    def elaborate(self, platform):
        m = Module()

        for cd in self.clockdomains:
            m.submodules[cd] = ClockDebug(cd)

        return m


class ClockDebug(Elaboratable):
    def __init__(self, domain_name, reset_less=False):
        self.domain_name = domain_name
        self.reset_less = reset_less

        self.counter = StatusSignal(32)
        self.is_reset = StatusSignal()

    def elaborate(self, platform):
        m = Module()

        m.d[self.domain_name] += self.counter.eq(self.counter + 1)
        m.d.comb += self.is_reset.eq(ResetSignal(self.domain_name))

        return m

    @driver_property
    def mhz(self):
        from time import sleep, time
        initial_counter = self.counter
        start = time()
        sleep(0.1)
        counter_difference = (self.counter - initial_counter)
        return counter_difference * (1 / (time() - start)) / 1e6
