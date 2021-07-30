# set up and demonstrate SPI connection to CMV12k control pins

from nmigen import *
from naps import *

class Top(Elaboratable):
    def __init__(self):
        self.sensor_reset = ControlSignal()

    def elaborate(self, platform: BetaPlatform):
        m = Module()

        platform.ps7.fck_domain(requested_frequency=100e6)

        sensor = platform.request("sensor")
        platform.ps7.fck_domain(250e6, "sensor_clk")
        m.d.comb += sensor.lvds_clk.eq(ClockSignal("sensor_clk"))
        m.d.comb += sensor.reset.eq(self.sensor_reset)

        m.submodules.sensor_spi = Cmv12kSpi(platform.request("sensor_spi"))

        return m

if __name__ == "__main__":
    cli(Top, runs_on=(BetaPlatform, ), possible_socs=(ZynqSocPlatform, ))
