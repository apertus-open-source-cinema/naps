# set up and demonstrate training of CMV12k

# DEMO PROCEDURE:
# 1. build the fatbitstream with `python3 applets/cmv12k/train_test.py -b`
# 2. copy the resulting build/train_test_*/train_test.fatbitstream.sh file to the Beta
# 3. log into the Beta and get root access with e.g. `sudo su`
# 4. power up the sensor with `axiom_power_init.sh && axiom_power_on.sh`
# 5. load the fatbitstream with `./train_test.fatbitstream.sh --run`
# 6. run the `design.train()` function at the prompt
# 7. if everything worked, you will see "working channel mask: 0xFFFFFFFF"

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

        m.d.comb += [
            sensor.frame_req.eq(0),
            sensor.t_exp1.eq(0),
            sensor.t_exp2.eq(0),
        ]

        m.submodules.sensor_spi = Cmv12kSpi(platform.request("sensor_spi"))
        sensor_rx = m.submodules.sensor_rx = Cmv12kRx(sensor)

        return m

    @driver_method
    def train(self):
        self.sensor_rx.configure_sensor_defaults(self.sensor_spi)
        self.sensor_rx.trainer.train(self.sensor_spi)

if __name__ == "__main__":
    cli(Top, runs_on=(BetaPlatform, ), possible_socs=(ZynqSocPlatform, ))
