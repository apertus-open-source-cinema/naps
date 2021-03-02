# Provides a linux framebuffer via HDMI

from nmigen import *
from naps import *


class Top(Elaboratable):
    def __init__(self):
        self.width = 1280
        self.height = 720

    def elaborate(self, platform: ZynqSocPlatform):
        if not isinstance(platform, ZyboPlatform):
            hdmi_plugin_connect(platform, "north")

        m = Module()

        cpu_writer = m.submodules.cpu_writer = DramPacketRingbufferCpuWriter(
            max_packet_size=0x1000000, n_buffers=1,
            default_packet_size=self.width * self.height * 4
        )

        platform.ps7.fck_domain(100e6, "axi_hp")

        p = Pipeline(m, start_domain="axi_hp")
        p += DramPacketRingbufferStreamReader(cpu_writer)
        p += SimpleStreamGearbox(p.output, target_width=32)
        p += StreamResizer(p.output, target_width=24)
        p += PacketizedStream2ImageStream(p.output, width=self.width)
        p += BufferedAsyncStreamFIFO(p.output, depth=16 * 1024, o_domain="pix")

        hdmi = platform.request("hdmi", "north")
        p += HdmiStreamSink(p.output, hdmi, generate_modeline(self.width, self.height, 30), pix_domain="pix")

        m.submodules.clocking_debug = ClockingDebug("pix", "pix_5x", "axi_hp")

        overlay_content = """
            %overlay_name%: framebuffer@%address% {
                compatible = "simple-framebuffer";
                reg = <0x%address% (%width% * %height% * 4)>;
                width = <%width%>;
                height = <%height%>;
                stride = <(%width% * 4)>;
                format = "a8b8g8r8";
            };
        """
        devicetree_overlay(platform, "framebuffer", overlay_content, {
            "width": str(self.width),
            "height": str(self.height),
            "address": "{:x}".format(cpu_writer.buffer_base_list[0]),
        })

        return m


if __name__ == "__main__":
    cli(Top, runs_on=(MicroR2Platform, BetaPlatform, ZyboPlatform), possible_socs=(ZynqSocPlatform, ))
