from nmigen import *

from cores.mmio_gpio import MmioGpio
from soc.cli import cli

from soc.zynq import ZynqSocPlatform


class Top(Elaboratable):
    def elaborate(self, platform: ZynqSocPlatform):
        m = Module()

        usb3_plugin = platform.request("usb3_plugin", "north")
        m.submodules.mmio_gpio = MmioGpio(usb3_plugin.gpio)

        return m


if __name__ == "__main__":
    with cli(Top) as platform:
        from devices.plugins.generic import generic_plugin_connect
        generic_plugin_connect(platform, "north")
