# A simple experiment that demonstrates basic CSR / SOC functionality
from nmigen import *
from nmigen.vendor.lattice_machxo_2_3l import LatticeMachXO2Platform
from nap import *
from nap.vendor.lattice_machxo2 import Osc


class Top(Elaboratable):
    def __init__(self):
        self.counter = StatusSignal(32)
        self.test_reg32 = ControlSignal(32)

    def elaborate(self, platform):
        m = Module()

        if isinstance(platform, ZynqSocPlatform):
            platform.ps7.fck_domain(requested_frequency=100e6)
            m.d.sync += self.counter.eq(self.counter + 1)
        elif isinstance(platform, LatticeMachXO2Platform):
            print("using lattice osc")
            m.submodules.osc = Osc()
            m.d.sync += self.counter.eq(self.counter + 1)
        else:
            m.d.comb += self.counter.eq(42)  # we dont have a clock source so we cant count

        if isinstance(platform, Usb3PluginPlatform):
            m.d.comb += platform.request("led", 0).eq(platform.jtag_active)

        return m


if __name__ == "__main__":
    cli(Top, runs_on=(Usb3PluginPlatform, MicroR2Platform, ZyboPlatform, BetaPlatform, HdmiDigitizerPlatform, BetaRFWPlatform), possible_socs=(JTAGSocPlatform, ZynqSocPlatform))
