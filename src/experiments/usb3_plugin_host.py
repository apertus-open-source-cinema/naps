# An experiment that allows to flash the USB3 plugin module via JTAG on the micro via bitbanging and
# MMIO GPIO.

from nmigen import *

from cores.mmio_gpio import MmioGpio
from cores.plugin_module_streamer.tx import PluginModuleStreamerTx
from cores.primitives.xilinx_s7.clocking import Pll
from cores.stream.counter_source import CounterStreamSource
from devices import MicroR2Platform
from soc.cli import cli

from soc.platforms.zynq import ZynqSocPlatform


class Top(Elaboratable):
    def elaborate(self, platform: ZynqSocPlatform):
        m = Module()

        platform.ps7.fck_domain(50e6, "fclk_in")
        pll = m.submodules.pll = Pll(50e6, 16, 1, input_domain="fclk_in")
        pll.output_domain("bitclk", 4)
        pll.output_domain("sync", 16)

        usb3_plugin = platform.request("usb3_plugin", "north")

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

        counter = m.submodules.counter = CounterStreamSource(32)
        m.submodules.tx = PluginModuleStreamerTx(usb3_plugin.lvds, counter.output, bitclk_domain="bitclk")

        return m


if __name__ == "__main__":
    with cli(Top, runs_on=(MicroR2Platform,), possible_socs=(ZynqSocPlatform,)) as platform:
        from devices.plugins.usb3_plugin_resource import usb3_plugin_connect
        usb3_plugin_connect(platform, "north")
