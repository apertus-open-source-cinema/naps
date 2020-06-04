from nmigen import *

from devices.zybo_platform import ZyboPlatform
from hdmi.hdmi import Hdmi
from hdmi.cvt import generate_modeline
from soc import cli

from soc.zynq import ZynqSocPlatform


class Top(Elaboratable):
    def elaborate(self, platform: ZynqSocPlatform):
        m = Module()

        hdmi_plugin = platform.request("hdmi", "north")
        m.submodules.hdmi = Hdmi(hdmi_plugin, generate_modeline(1920, 1080, 30))

        return m


if __name__ == "__main__":
    with cli(Top) as platform:
        if not isinstance(platform, ZyboPlatform):
            from devices.hdmi_plugin import hdmi_plugin_connect
            hdmi_plugin_connect(platform, "north")
