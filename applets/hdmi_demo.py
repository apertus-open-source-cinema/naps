# Test HDMI output using a given modeline by displaying a solid (adjustable) color

from nmigen import *
from naps import *


class Top(Elaboratable):
    def __init__(self):
        self.r = ControlSignal(8, reset=0xFA)
        self.g = ControlSignal(8, reset=0x87)
        self.b = ControlSignal(8, reset=0x56)

    def elaborate(self, platform: ZynqSocPlatform):
        if not isinstance(platform, ZyboPlatform):
            hdmi_plugin_connect(platform, "north")

        m = Module()

        hdmi_resource = platform.request("hdmi", "north")
        hdmi = m.submodules.hdmi = HdmiTx(hdmi_resource, generate_modeline(1920, 1080, 30))

        clocking_debug = m.submodules.clocking_debug = ClockingDebug("pix", "pix_5x")
        
        m.d.comb += hdmi.rgb.r.eq(self.r)
        m.d.comb += hdmi.rgb.g.eq(self.g)
        m.d.comb += hdmi.rgb.b.eq(self.b)

        return m


if __name__ == "__main__":
    cli(Top, runs_on=(MicroR2Platform, BetaPlatform, ZyboPlatform), possible_socs=(ZynqSocPlatform, ))
