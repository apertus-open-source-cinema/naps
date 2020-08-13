# A simple experiment that demonstrates basic CSR / SOC functionality

from nmigen import *

from cores.blink_debug import BlinkDebug
from cores.csr_bank import StatusSignal, ControlSignal
from cores.primitives.lattice_machxo2.clocking import Osc
from devices import Usb3PluginPlatform, MicroR2Platform, ZyboPlatform, BetaPlatform, HdmiDigitizerPlatform
from soc.cli import cli


class Top(Elaboratable):
    def __init__(self):
        self.counter = StatusSignal(32)
        self.test_reg = ControlSignal(32)

    def elaborate(self, platform):
        m = Module()

        m.submodules.osc = Osc()
        m.d.sync += self.counter.eq(self.counter + 1)

        return m


if __name__ == "__main__":
    with cli(Top, runs_on=(Usb3PluginPlatform, MicroR2Platform, ZyboPlatform, BetaPlatform, HdmiDigitizerPlatform)) as platform:
        pass
