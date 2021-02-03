# Test HDMI output using a given modeline by displaying a solid (adjustable) color

from nmigen import *

from devices import MicroR2Platform, BetaPlatform, ZyboPlatform
from lib.debug.clocking_debug import ClockingDebug
from lib.io.hdmi.cvt_python import generate_modeline
from lib.io.hdmi.hdmi import Hdmi
from lib.peripherals.csr_bank import ControlSignal
from soc.cli import cli
from soc.platforms.zynq import ZynqSocPlatform


class Top(Elaboratable):
    def __init__(self):
        self.r = ControlSignal(8, reset=0xFA)
        self.g = ControlSignal(8, reset=0x87)
        self.b = ControlSignal(8, reset=0x56)

    def elaborate(self, platform: ZynqSocPlatform):
        from devices.zybo_platform import ZyboPlatform
        if not isinstance(platform, ZyboPlatform):
            from devices.plugins.hdmi_plugin_resource import hdmi_plugin_connect
            hdmi_plugin_connect(platform, "north")

        m = Module()

        hdmi_resource = platform.request("hdmi", "north")
        hdmi = m.submodules.hdmi = Hdmi(hdmi_resource, generate_modeline(1920, 1080, 60))

        clocking_debug = m.submodules.clocking_debug = ClockingDebug("pix", "pix_5x")
        
        m.d.comb += hdmi.rgb.r.eq(self.r)
        m.d.comb += hdmi.rgb.g.eq(self.g)
        m.d.comb += hdmi.rgb.b.eq(self.b)

        return m


if __name__ == "__main__":
    cli(Top, runs_on=(MicroR2Platform, BetaPlatform, ZyboPlatform), possible_socs=(ZynqSocPlatform, ))
