# An experiment that glues everything together and tries to get a full sensor -> hdmi flow working on the micro
import os
from nmigen import *
from naps import *


class Top(Elaboratable):
    def __init__(self):
        self.sensor_reset_n = ControlSignal(name='sensor_reset', reset=1)

    def elaborate(self, platform):
        from naps.platform.plugins.hdmi_plugin_resource import hdmi_plugin_connect
        hdmi_plugin_connect(platform, "north")

        m = Module()

        platform.ps7.fck_domain(143e6, "axi_hp")

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
            "set_property CLOCK_DEDICATED_ROUTE FALSE [get_nets pin_sensor_0__lvds_clk/input_hispi_rx_sensor_0__lvds_clk__i]"

        ip = Pipeline(m, prefix="input")
        ip += HispiRx(sensor, hispi_domain="hispi")

        ip += BufferedAsyncStreamFIFO(ip.output, 2048, o_domain="axi_hp")
        ip += StreamResizer(ip.output, 64)
        ip += ImageStream2PacketizedStream(ip.output)
        ip += DramPacketRingbufferStreamWriter(ip.output, max_packet_size=0x800000, n_buffers=4)
        dram_writer = ip.last
        ip += DramPacketRingbufferCpuReader(dram_writer)

        # Output pipeline
        op = Pipeline(m, prefix="output", start_domain="axi_hp")
        op += DramPacketRingbufferStreamReader(dram_writer)
        op += StreamResizer(op.output, 48)
        op += StreamGearbox(op.output, target_width=12)
        op += PacketizedStream2ImageStream(op.output, 2304)
        op += StreamResizer(op.output, 8, upper_bits=True)
        op += StreamBuffer(op.output)
        op += SimpleInterpolatingDebayerer(op.output, 2304, 1296)
        op += StreamBuffer(op.output)
        op += VideoResizer(op.output, 2560, 1440)

        op += BufferedAsyncStreamFIFO(op.output, depth=32 * 1024, o_domain="pix")

        hdmi = platform.request("hdmi", "north")
        op += HdmiStreamSink(op.output, hdmi, generate_modeline(2560, 1440, 30), pix_domain="pix")  # TODO: the domain handling here stinks

        return m

    @driver_method
    def kick_sensor(self):
        from os import system
        system("cat /axiom-api/scripts/kick/value")


if __name__ == "__main__":
    cli(Top, runs_on=(MicroR2Platform,), possible_socs=(ZynqSocPlatform,))
