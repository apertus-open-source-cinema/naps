# Provides a linux framebuffer via HDMI

from nmigen import *

from lib.bus.ring_buffer import RingBufferAddressStorage
from lib.bus.stream.fifo import BufferedAsyncStreamFIFO
from lib.debug.clocking_debug import ClockingDebug
from lib.io.hdmi.hdmi import Hdmi
from lib.io.hdmi.hdmi_stream_sink import HdmiStreamAligner, HdmiStreamSink
from lib.video.buffer_reader import VideoBufferReader
from lib.io.hdmi.cvt_python import generate_modeline
from devices import MicroR2Platform, BetaPlatform, ZyboPlatform
from soc.cli import cli
from soc.devicetree.overlay import devicetree_overlay
from soc.platforms.zynq import ZynqSocPlatform


class Top(Elaboratable):
    def __init__(self):
        self.width = 1920
        self.height = 1080
        self.fps = 30

    def elaborate(self, platform: ZynqSocPlatform):
        m = Module()

        ring_buffer = RingBufferAddressStorage(buffer_size=0x1000000, n=1)

        platform.ps7.fck_domain(200e6, "axi_hp")
        buffer_reader = m.submodules.buffer_reader = DomainRenamer("axi_hp")(VideoBufferReader(
            ring_buffer, bits_per_pixel=32,
            width_pixels=self.width, height_pixels=self.height,
        ))

        fifo = m.submodules.fifo = BufferedAsyncStreamFIFO(
            buffer_reader.output, depth=32 * 1024, i_domain="axi_hp", o_domain="pix"
        )

        hdmi_plugin = platform.request("hdmi", "north")
        m.submodules.hdmi_stream_sink = HdmiStreamSink(
            fifo.output, hdmi_plugin,
            generate_modeline(self.width, self.height, self.fps),
            pix_domain="pix"
        )

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
            "address": "{:x}".format(ring_buffer.buffer_base_list[0]),
        })

        return m


if __name__ == "__main__":
    with cli(Top, runs_on=(MicroR2Platform, BetaPlatform, ZyboPlatform), possible_socs=(ZynqSocPlatform, )) as platform:
        from devices.zybo_platform import ZyboPlatform
        if not isinstance(platform, ZyboPlatform):
            from devices.plugins.hdmi_plugin_resource import hdmi_plugin_connect
            hdmi_plugin_connect(platform, "north")
