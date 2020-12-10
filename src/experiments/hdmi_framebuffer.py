# Provides a linux framebuffer via HDMI

from nmigen import *

from devices import MicroR2Platform, BetaPlatform, ZyboPlatform
from lib.bus.ring_buffer import RingBufferAddressStorage
from lib.bus.stream.fifo import BufferedAsyncStreamFIFO
from lib.bus.stream.gearbox import SimpleStreamGearbox
from lib.debug.clocking_debug import ClockingDebug
from lib.io.hdmi.cvt_python import generate_modeline
from lib.io.hdmi.hdmi_stream_sink import HdmiStreamSink
from lib.video.buffer_reader import VideoBufferReader
from lib.video.resizer import VideoResizer
from soc.cli import cli
from soc.devicetree.overlay import devicetree_overlay
from soc.platforms.zynq import ZynqSocPlatform


class Top(Elaboratable):
    def __init__(self):
        self.width = 1280
        self.height = 720

    def elaborate(self, platform: ZynqSocPlatform):
        m = Module()

        ring_buffer = RingBufferAddressStorage(buffer_size=0x1000000, n=1)

        platform.ps7.fck_domain(200e6, "axi_hp")
        buffer_reader = m.submodules.buffer_reader = DomainRenamer("axi_hp")(VideoBufferReader(
            ring_buffer, bits_per_pixel=32,
            width_pixels=self.width, height_pixels=self.height,
        ))

        gearbox = m.submodules.gearbox = DomainRenamer("axi_hp")(SimpleStreamGearbox(buffer_reader.output, target_width=32))
        resizer = m.submodules.resizer = DomainRenamer("axi_hp")(VideoResizer(gearbox.output, 1920, 1080))

        fifo = m.submodules.fifo = BufferedAsyncStreamFIFO(
            resizer.output, depth=16 * 1024, i_domain="axi_hp", o_domain="pix"
        )

        hdmi = platform.request("hdmi", "north")
        m.submodules.hdmi_stream_sink = HdmiStreamSink(
            fifo.output, hdmi,
            generate_modeline(1920, 1080, 30),
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
