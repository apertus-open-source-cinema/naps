from nmigen import *

from cores.csr_bank import ControlSignal
from soc.cli import cli
from cores.mmio_gpio import MmioGpio


class Top(Elaboratable):
    def __init__(self):
        self.sensor_reset = ControlSignal(name='sensor_reset')

    def elaborate(self, platform):
        m = Module()

        i2c_pads = platform.request("i2c")
        m.submodules.i2c = MmioGpio(i2c_pads)

        sensor = platform.request("sensor")
        ps7 = platform.get_ps7()
        ps7.fck_domain(24e6)
        m.d.comb += sensor.clk.eq(ClockSignal())
        m.d.comb += sensor.reset.eq(self.sensor_reset)

        return m


if __name__ == "__main__":
    cli(Top)
