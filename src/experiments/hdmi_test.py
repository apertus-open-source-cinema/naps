# Test HDMI using a given modeline

from nmigen import *

from cores.hdmi.hdmi import Hdmi
from devices import MicroR2Platform, BetaPlatform, ZyboPlatform
from soc.cli import cli
from soc.platforms.zynq import ZynqSocPlatform


class Top(Elaboratable):
    def elaborate(self, platform: ZynqSocPlatform):
        m = Module()

        hdmi_plugin = platform.request("hdmi", "north")
        m.submodules.hdmi = Hdmi(hdmi_plugin, modeline='Modeline "Mode 1" 148.500 1920 2008 2052 2200 1080 1084 1089 1125 +hsync +vsync')

        return m


if __name__ == "__main__":
    with cli(Top, runs_on=(MicroR2Platform, BetaPlatform, ZyboPlatform)) as platform:
        from devices.zybo_platform import ZyboPlatform
        if not isinstance(platform, ZyboPlatform):
            from devices.plugins.hdmi_plugin_resource import hdmi_plugin_connect
            hdmi_plugin_connect(platform, "north")
