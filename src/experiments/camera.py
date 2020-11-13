# An experiment that glues everything together and tries to get a full sensor -> hdmi flow working on the micro
import os

from nmigen import *

from devices import MicroR2Platform
from lib.bus.axi.buffer_writer import AxiBufferWriter
from lib.bus.ring_buffer import RingBufferAddressStorage
from lib.bus.stream.fifo import BufferedAsyncStreamFIFO
from lib.bus.stream.gearbox import StreamGearbox, StreamResizer
from lib.debug.clocking_debug import ClockingDebug
from lib.io.hdmi.cvt_python import generate_modeline
from lib.io.hdmi.hdmi_stream_sink import HdmiStreamSink
from lib.io.hispi.hispi import Hispi
from lib.peripherals.csr_bank import ControlSignal
from lib.peripherals.i2c.bitbang_i2c import BitbangI2c
from lib.video.buffer_reader import VideoBufferReader
from lib.video.debayer import SimpleFullResDebayerer
from lib.video.resizer import VideoResizer
from lib.video.stream_converter import ImageStream2PacketizedStream
from soc.cli import cli
from soc.platforms import ZynqSocPlatform
from soc.pydriver.drivermethod import driver_method


class Top(Elaboratable):
    def __init__(self):
        self.sensor_reset_n = ControlSignal(name='sensor_reset', reset=1)

    def elaborate(self, platform):
        m = Module()

        platform.ps7.fck_domain(200e6, "axi_hp")
        ring_buffer = RingBufferAddressStorage(buffer_size=0x1000000, n=4)

        # Control Pane
        m.submodules.clocking_debug = ClockingDebug("pix", "pix_5x", "axi_hp", "hispi")

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
        writer_fifo = m.submodules.writer_fifo = BufferedAsyncStreamFIFO(
            hispi.output, 2048, i_domain="hispi", o_domain="axi_hp"
        )
        input_stream_resizer = m.submodules.input_stream_resizer = DomainRenamer("axi_hp")(StreamResizer(writer_fifo.output, 64))
        converter = m.submodules.converter = DomainRenamer("axi_hp")(ImageStream2PacketizedStream(input_stream_resizer.output))
        m.submodules.buffer_writer = DomainRenamer("axi_hp")(AxiBufferWriter(ring_buffer, converter.output))

        # Output pipeline
        buffer_reader = m.submodules.buffer_reader = DomainRenamer("axi_hp")(VideoBufferReader(
            ring_buffer, bits_per_pixel=16,
            width_pixels=2304, height_pixels=1296,
        ))
        output_stream_resizer = m.submodules.output_stream_resizer = DomainRenamer("axi_hp")(StreamResizer(buffer_reader.output, 48))
        output_gearbox = m.submodules.output_gearbox = DomainRenamer("axi_hp")(
            StreamGearbox(output_stream_resizer.output, target_width=12)
        )
        debayerer = m.submodules.debayerer = DomainRenamer("axi_hp")(SimpleFullResDebayerer(output_gearbox.output))
        output_video_resizer = m.submodules.output_video_resizer = DomainRenamer("axi_hp")(VideoResizer(debayerer.output, 2560, 1440))
        reader_fifo = m.submodules.reader_fifo = BufferedAsyncStreamFIFO(
            output_video_resizer.output, depth=32 * 1024, i_domain="axi_hp", o_domain="pix"
        )

        hdmi_plugin = platform.request("hdmi", "north")
        m.submodules.hdmi_stream_sink = HdmiStreamSink(
            reader_fifo.output, hdmi_plugin,
            generate_modeline(2560, 1440, 30),
            pix_domain="pix"
        )

        return m

    @driver_method
    def dump_buffer(self):
        self.writer_reset = 1
        self.writer_reset = 0
        enable_bitslip = self.hispi.phy.enable_bitslip
        self.hispi.phy.enable_bitslip = 0
        from time import sleep
        sleep(0.1)
        from os import system
        system("sudo dd if=/dev/mem bs=4096 skip=260046848 count=16777216 iflag=skip_bytes,count_bytes of=buffer.out")
        self.hispi.phy.enable_bitslip = enable_bitslip

    @driver_method
    def kick_sensor(self):
        from os import system
        system("cat /axiom-api/scripts/kick/value")


if __name__ == "__main__":
    with cli(Top, runs_on=(MicroR2Platform,), possible_socs=(ZynqSocPlatform,)) as platform:
        from devices.plugins.hdmi_plugin_resource import hdmi_plugin_connect

        hdmi_plugin_connect(platform, "north")
