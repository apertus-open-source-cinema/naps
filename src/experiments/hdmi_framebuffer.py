# Provides a linux framebuffer via HDMI

from nmigen import *

from devices import MicroR2Platform, BetaPlatform, ZyboPlatform
from lib.bus.stream.fifo import BufferedAsyncStreamFIFO
from lib.bus.stream.gearbox import SimpleStreamGearbox, StreamResizer
from lib.bus.stream.pipeline import Pipeline
from lib.debug.clocking_debug import ClockingDebug
from lib.dram_packet_ringbuffer.cpu_if import DramPacketRingbufferCpuWriter
from lib.dram_packet_ringbuffer.stream_if import DramPacketRingbufferStreamReader
from lib.io.hdmi.cvt_python import generate_modeline
from lib.io.hdmi.hdmi_stream_sink import HdmiStreamSink
from lib.video.adapters import PacketizedStream2ImageStream
from soc.cli import cli
from soc.devicetree.overlay import devicetree_overlay
from soc.platforms.zynq import ZynqSocPlatform


class Top(Elaboratable):
    def __init__(self):
        self.width = 1280
        self.height = 720

    def elaborate(self, platform: ZynqSocPlatform):
        from devices.zybo_platform import ZyboPlatform
        if not isinstance(platform, ZyboPlatform):
            from devices.plugins.hdmi_plugin_resource import hdmi_plugin_connect
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
