# A simple experiment that demonstrates basic CSR / SOC functionality
from itertools import count

from nmigen import *

from cores.csr_bank import StatusSignal, ControlSignal
from devices import Usb3PluginPlatform, MicroR2Platform, ZyboPlatform, BetaPlatform, HdmiDigitizerPlatform
from soc.cli import cli
from util.nmigen_misc import connect_leds


class Top(Elaboratable):
    def __init__(self):
        self.counter = StatusSignal(32)
        self.test_reg = ControlSignal(32)

    def elaborate(self, platform):
        m = Module()

        if hasattr(platform, "default_clk"):
            m.d.sync += self.counter.eq(self.counter + 1)
        connect_leds(m, platform, self.counter, upper_bits=True)

        return m


if __name__ == "__main__":
    with cli(Top, runs_on=(Usb3PluginPlatform, MicroR2Platform, ZyboPlatform, BetaPlatform, HdmiDigitizerPlatform)) as platform:
        pass
