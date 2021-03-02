# An experiment that allows to flash the USB3 plugin module via JTAG on the micro via bitbanging and
# MMIO GPIO.
from nmigen import *
from naps import *
from naps.vendor.xilinx_s7 import Pll


class Top(Elaboratable):
    def elaborate(self, platform: ZynqSocPlatform):
        usb3_plugin_connect(platform, "south")

        m = Module()

        platform.ps7.fck_domain(20e6, "fclk_in")
        pll = m.submodules.pll = Pll(20e6, 40, 1, input_domain="fclk_in")
        pll.output_domain("bitclk", 2)
        pll.output_domain("sync", 8)

        clocking = m.submodules.clocking = ClockingDebug("fclk_in", "bitclk", "sync")

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

        counter = m.submodules.counter = CounterStreamSource(32)
        m.submodules.tx = PluginModuleStreamerTx(usb3_plugin.lvds, counter.output, bitclk_domain="bitclk")

        return m


if __name__ == "__main__":
    cli(Top, runs_on=(MicroR2Platform,), possible_socs=(ZynqSocPlatform,))
