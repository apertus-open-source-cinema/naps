# Test HDMI output using a given modeline by displaying a solid (adjustable) color

from nmigen import *

from cores.csr_bank import ControlSignal
from cores.debug.clocking_debug import ClockingDebug
from cores.hdmi.cvt_python import generate_modeline
from cores.hdmi.hdmi import Hdmi
from devices import MicroR2Platform, BetaPlatform, ZyboPlatform
from soc.cli import cli
from soc.platforms.zynq import ZynqSocPlatform


class Top(Elaboratable):
    def __init__(self):
        self.r = ControlSignal(8, reset=0xFA)
        self.g = ControlSignal(8, reset=0x87)
        self.b = ControlSignal(8, reset=0x56)

    def elaborate(self, platform: ZynqSocPlatform):
        m = Module()

        hdmi_plugin = platform.request("hdmi", "north")
        hdmi = m.submodules.hdmi = Hdmi(hdmi_plugin, generate_modeline(1920, 1080, 60))

        clocking_debug = m.submodules.clocking_debug = ClockingDebug("pix", "pix_5x")
        
        m.d.comb += hdmi.rgb.r.eq(self.r)
        m.d.comb += hdmi.rgb.g.eq(self.g)
        m.d.comb += hdmi.rgb.b.eq(self.b)

        return m


if __name__ == "__main__":
    with cli(Top, runs_on=(MicroR2Platform, BetaPlatform, ZyboPlatform), possible_socs=(ZynqSocPlatform, )) as platform:
        from devices.zybo_platform import ZyboPlatform
        if not isinstance(platform, ZyboPlatform):
            from devices.plugins.hdmi_plugin_resource import hdmi_plugin_connect
            hdmi_plugin_connect(platform, "north")
