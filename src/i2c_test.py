from nmigen import *

from soc import cli
from soc.peripherals.mmio_gpio import MmioGpio


class Top(Elaboratable):
    def elaborate(self, platform):
        m = Module()

        i2c_pads = platform.request("i2c")
        m.submodules.i2c = MmioGpio(i2c_pads)

        return m


if __name__ == "__main__":
    cli(Top)
