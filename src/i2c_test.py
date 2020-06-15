import os

from nmigen import *

from cores.bitbang_i2c import BitbangI2c
from cores.csr_bank import ControlSignal
from cores.hispi.hispi import Hispi
from soc.cli import cli


class Top(Elaboratable):
    def __init__(self):
        self.sensor_reset_n = ControlSignal(name='sensor_reset', reset=1)

    def elaborate(self, platform):
        m = Module()

        i2c_pads = platform.request("i2c")
        m.submodules.i2c = BitbangI2c(i2c_pads)

        sensor = platform.request("sensor")
        ps7 = platform.get_ps7()
        ps7.fck_domain(24e6)
        m.d.comb += sensor.clk.eq(ClockSignal())
        m.d.comb += sensor.reset.eq(~self.sensor_reset_n)
        # TODO: find more ideomatic way to do this
        os.environ["NMIGEN_add_constraints"] = "set_property CLOCK_DEDICATED_ROUTE FALSE [get_nets pin_sensor_0__lvds_clk/hispi_sensor_0__lvds_clk__i]"

        m.submodules.hispi = Hispi(sensor)

        return m


if __name__ == "__main__":
    with cli(Top) as platform:
        pass
