# An experiment that glues everything together and tries to get a full sensor -> hdmi flow working on the micro
import os

from nmigen import *

from devices import MicroR2Platform
from lib.bus.axi.buffer_writer import AxiBufferWriter
from lib.bus.ring_buffer import RingBufferAddressStorage
from lib.bus.stream.debug import StreamInfo
from lib.bus.stream.fifo import BufferedAsyncStreamFIFO, BufferedSyncStreamFIFO
from lib.bus.stream.gearbox import StreamGearbox, StreamResizer
from lib.debug.clocking_debug import ClockingDebug
from lib.io.hdmi.cvt_python import generate_modeline
from lib.io.hdmi.hdmi_stream_sink import HdmiStreamSink
from lib.io.hispi.hispi import Hispi
from lib.peripherals.csr_bank import ControlSignal
from lib.peripherals.i2c.bitbang_i2c import BitbangI2c
from lib.video.buffer_reader import VideoBufferReader
from lib.video.debayer import RecoloringDebayerer, SimpleInterpolatingDebayerer
from lib.video.focus_peeking import FocusPeeking
from lib.video.resizer import VideoResizer
from lib.video.stream_converter import ImageStream2PacketizedStream
from lib.video.demo_source import BlinkDemoVideoSource
from soc.cli import cli
from soc.platforms import ZynqSocPlatform
from soc.pydriver.drivermethod import driver_method


class Top(Elaboratable):
    def __init__(self):
        self.sensor_reset_n = ControlSignal(name='sensor_reset', reset=1)

    def elaborate(self, platform):
        m = Module()

        platform.ps7.fck_domain(143e6, "axi_hp")
        ring_buffer = RingBufferAddressStorage(buffer_size=0x800000, n=4)

        # Control Pane
        i2c_pads = platform.request("i2c")
        m.submodules.i2c = BitbangI2c(i2c_pads)

        # Input Pipeline
        sensor = platform.request("sensor")
        platform.ps7.fck_domain(24e6, "sensor_clk")
        m.d.comb += sensor.clk.eq(ClockSignal("sensor_clk"))
        m.d.comb += sensor.reset.eq(~self.sensor_reset_n)
        # TODO: find more idiomatic way to do this
        os.environ["NMIGEN_add_constraints"] = \
            "set_property CLOCK_DEDICATED_ROUTE FALSE [get_nets pin_sensor_0__lvds_clk/hispi_sensor_0__lvds_clk__i]"

        hispi = m.submodules.hispi = Hispi(sensor, hispi_domain="hispi")
        input_fifo = m.submodules.input_fifo = BufferedAsyncStreamFIFO(
            hispi.output, 2048, i_domain="hispi", o_domain="axi_hp"
        )
        input_stream_resizer = m.submodules.input_stream_resizer = DomainRenamer("axi_hp")(StreamResizer(input_fifo.output, 64))
        input_converter = m.submodules.input_converter = DomainRenamer("axi_hp")(ImageStream2PacketizedStream(input_stream_resizer.output))
        m.submodules.input_writer = DomainRenamer("axi_hp")(AxiBufferWriter(ring_buffer, input_converter.output))

        # Output pipeline
        output_reader = m.submodules.output_reader = DomainRenamer("axi_hp")(VideoBufferReader(
            ring_buffer, bits_per_pixel=16,
            width_pixels=2304, height_pixels=1296,
        ))
        output_stream_resizer = m.submodules.output_stream_resizer = DomainRenamer("axi_hp")(StreamResizer(output_reader.output, 48))
        output_gearbox = m.submodules.output_gearbox = DomainRenamer("axi_hp")(
            StreamGearbox(output_stream_resizer.output, target_width=12)
        )
        output_resizer_12_to_8 = m.submodules.output_resizer_12_to_8 = StreamResizer(output_gearbox.output, 8, upper_bits=True)
        debayerer = m.submodules.debayerer = DomainRenamer("axi_hp")(SimpleInterpolatingDebayerer(output_resizer_12_to_8.output, 2304, 1296))
        output_after_debayer_fifo = m.submodules.output_after_debayer_fifo = DomainRenamer("axi_hp")(BufferedSyncStreamFIFO(debayerer.output, 32))
        output_focus = m.submodules.output_focus = DomainRenamer("axi_hp")(FocusPeeking(output_after_debayer_fifo.output, 2304, 1296))
        output_after_focus_fifo = m.submodules.output_after_focus = DomainRenamer("axi_hp")(BufferedSyncStreamFIFO(output_focus.output, 32))
        output_video_resizer = m.submodules.output_video_resizer = DomainRenamer("axi_hp")(VideoResizer(output_after_focus_fifo.output, 2560, 1440))
        output_fifo = m.submodules.output_fifo = BufferedAsyncStreamFIFO(
            output_video_resizer.output, depth=32 * 1024, i_domain="axi_hp", o_domain="pix"
        )

        hdmi_plugin = platform.request("hdmi", "north")
        m.submodules.hdmi_stream_sink = HdmiStreamSink(
            output_fifo.output, hdmi_plugin,
            generate_modeline(2560, 1440, 30),
            pix_domain="pix"
        )

        return m

    @driver_method
    def kick_sensor(self):
        from os import system
        system("cat /axiom-api/scripts/kick/value")


if __name__ == "__main__":
    with cli(Top, runs_on=(MicroR2Platform,), possible_socs=(ZynqSocPlatform,)) as platform:
        from devices.plugins.hdmi_plugin_resource import hdmi_plugin_connect

        hdmi_plugin_connect(platform, "north")
