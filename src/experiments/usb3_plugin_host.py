# An experiment that allows to flash the USB3 plugin module via JTAG on the micro via bitbanging and
# MMIO GPIO.

from nmigen import *

from cores.mmio_gpio import MmioGpio
from devices import MicroR2Platform
from soc.cli import cli

from soc.platforms.zynq import ZynqSocPlatform


class Top(Elaboratable):
    def elaborate(self, platform: ZynqSocPlatform):
        m = Module()

        usb3_plugin = platform.request("generic_plugin", "north")
        m.submodules.mmio_gpio = MmioGpio([getattr(usb3_plugin, "gpio{}".format(i)) for i in range(8)])

        return m


if __name__ == "__main__":
    with cli(Top, runs_on=(MicroR2Platform, )) as platform:
        from devices.plugins.generic import generic_plugin_connect
        generic_plugin_connect(platform, "north")
