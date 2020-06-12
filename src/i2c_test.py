from nmigen import *

from soc.cli import cli
from cores.mmio_gpio import MmioGpio


class Top(Elaboratable):
    def elaborate(self, platform):
        m = Module()

        i2c_pads = platform.request("i2c")
        m.submodules.i2c = MmioGpio(i2c_pads)

        return m


if __name__ == "__main__":
    cli(Top)
