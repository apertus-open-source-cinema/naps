# A simple experiment that demonstrates basic CSR / SOC functionality
from nmigen import *
from nmigen.vendor.lattice_machxo_2_3l import LatticeMachXO2Platform
from naps import *
from naps.vendor.lattice_machxo2 import Osc


class Top(Elaboratable):
    def __init__(self):
        self.counter = StatusSignal(32)
        self.test_reg32 = ControlSignal(32)

    def elaborate(self, platform):
        m = Module()

        has_clk = False
        if isinstance(platform, ZynqSocPlatform):
            platform.ps7.fck_domain(requested_frequency=100e6)
            has_clk = True
        elif isinstance(platform, LatticeMachXO2Platform):
            m.submodules.osc = Osc()
            has_clk = True
        elif isinstance(platform, Colorlight5a75b70Platform):
            has_clk = True
            m.d.comb += platform.request("led", 0).o.eq(self.counter[22])

        if has_clk:
            m.d.sync += self.counter.eq(self.counter + 1)
        else:
            m.d.comb += self.counter.eq(42)  # we dont have a clock source so we cant count

        return m


if __name__ == "__main__":
    cli(
        Top,
        runs_on=(Usb3PluginPlatform, MicroR2Platform, ZyboPlatform, BetaPlatform, HdmiDigitizerPlatform, BetaRFWPlatform, Colorlight5a75b70Platform),
        possible_socs=(JTAGSocPlatform, ZynqSocPlatform)
    )
