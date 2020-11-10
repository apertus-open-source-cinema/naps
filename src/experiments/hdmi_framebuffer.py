# Provides a linux framebuffer via HDMI

from nmigen import *

from lib.bus.ring_buffer import RingBufferAddressStorage
from lib.io.hdmi.hdmi_buffer_reader import HdmiBufferReader, LinuxFramebuffer
from lib.io.hdmi.cvt_python import generate_modeline
from devices import MicroR2Platform, BetaPlatform, ZyboPlatform
from soc.cli import cli
from soc.platforms.zynq import ZynqSocPlatform


class Top(Elaboratable):
    def elaborate(self, platform: ZynqSocPlatform):
        m = Module()

        platform.ps7.fck_domain(200e6, "axi_hp")
        ring_buffer = RingBufferAddressStorage(buffer_size=0x1000000, n=1)
        hdmi_plugin = platform.request("hdmi", "north")
        m.submodules.hdmi_buffer_reader = HdmiBufferReader(
            ring_buffer, hdmi_plugin,
            modeline=generate_modeline(1920, 1080, 60),
            data_interpreter_class=LinuxFramebuffer
        )

        return m


if __name__ == "__main__":
    with cli(Top, runs_on=(MicroR2Platform, BetaPlatform, ZyboPlatform), possible_socs=(ZynqSocPlatform, )) as platform:
        from devices.zybo_platform import ZyboPlatform
        if not isinstance(platform, ZyboPlatform):
            from devices.plugins.hdmi_plugin_resource import hdmi_plugin_connect
            hdmi_plugin_connect(platform, "north")
