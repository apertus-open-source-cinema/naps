# An experiment that glues everything together and tries to get a full sensor -> usb3 flow working on the micro
import os
from nmigen import *
from naps import *
from naps.vendor.xilinx_s7 import Pll


class Top(Elaboratable):
    def __init__(self):
        self.sensor_reset_n = ControlSignal(name='sensor_reset', reset=1)

    def elaborate(self, platform):
        usb3_plugin_connect(platform, "south", gpio=isinstance(platform, MicroR2Platform))

        m = Module()

        platform.ps7.fck_domain(143e6, "axi_hp")

        # Control Pane
        m.submodules.clocking = ClockingDebug("usb3_fclk", "usb3_bitclk", "axi_hp")

        i2c_pads = platform.request("i2c")
        m.submodules.i2c = BitbangI2c(i2c_pads)

        usb3_plugin = platform.request("usb3_plugin", "south")
        if isinstance(platform, MicroR2Platform):
            m.submodules.mmio_gpio = MmioGpio([
                usb3_plugin.jtag.tms,
                usb3_plugin.jtag.tck,
                usb3_plugin.jtag.tdi,
                usb3_plugin.jtag.tdo,

                usb3_plugin.jtag_enb,
                usb3_plugin.program,
                usb3_plugin.init,
                usb3_plugin.done,
            ])

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

        # Output pipeline
        op = Pipeline(m, prefix="output", start_domain="axi_hp")
        op += DramPacketRingbufferStreamReader(dram_writer)
        op += StreamResizer(op.output, 48)
        op += StreamGearbox(op.output, target_width=12)
        op += StreamResizer(op.output, 8, upper_bits=True)
        op += StreamGearbox(op.output, target_width=32)

        platform.ps7.fck_domain(20e6, "usb3_fclk")
        pll = m.submodules.pll = Pll(20e6, 60, 1, input_domain="usb3_fclk")
        pll.output_domain("usb3_bitclk", 6)
        pll.output_domain("usb3_sync", 24)

        op += BufferedAsyncStreamFIFO(op.output, 1024, o_domain="usb3_sync")
        op += Ft60xLegalizer(op.output, packet_len=2304 * 1296)
        op += PluginModuleStreamerTx(usb3_plugin.lvds, op.output, bitclk_domain="usb3_bitclk")

        return m

    @driver_method
    def kick_sensor(self):
        from os import system
        system("cat /axiom-api/scripts/kick/value")


if __name__ == "__main__":
    cli(Top, runs_on=(MicroR2Platform,), possible_socs=(ZynqSocPlatform,))
