from nmigen import *

from cores.csr_bank import StatusSignal, ControlSignal
from soc.cli import cli


class Top(Elaboratable):
    def __init__(self):
        self.counter = StatusSignal(32)
        self.test_reg = ControlSignal(32)

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.counter.eq(self.counter + 1)
        leds = Cat(*[platform.request("led", i) for i in range(8)])
        m.d.comb += leds.eq(self.test_reg)

        return m


if __name__ == "__main__":
    with cli(Top) as platform:
        pass
