# set up and demonstrate capturing the test pattern of CMV12k

# DEMO PROCEDURE:
# 1. build the fatbitstream with `python3 applets/cmv12k/pattern_test.py -b`
# 2. copy the resulting build/pattern_test_*/pattern_test.zip file to the Beta
# 3. log into the Beta and get root access with e.g. `sudo su`
# 4. power up the sensor with `axiom_power_init.sh && axiom_power_on.sh`
# 5. load the fatbitstream with `./pattern_test.zip --run`
# 6. run `pattern = design.capture_pattern()` function at the prompt

from nmigen import *
from nmigen.lib.cdc import PulseSynchronizer
from naps import *

class Stats(Elaboratable):
    def __init__(self):
        self.data_valid_count = StatusSignal(32)
        self.line_valid_count = StatusSignal(32)
        self.frame_valid_count = StatusSignal(32)
        self.ctrl_value = StatusSignal(12)
        self.reset = PulseReg(1)

        self.ctrl_lane = Signal(12)
        self.ctrl_valid = Signal()

        self.frame_trigger = Signal()

    def elaborate(self, platform):
        m = Module()

        m.submodules += self.reset

        reset_sync = m.submodules.reset_sync = PulseSynchronizer(platform.csr_domain, "sync")
        m.d.comb += reset_sync.i.eq(self.reset.pulse)

        with m.If(reset_sync.o):
            m.d.sync += [
                self.data_valid_count.eq(0),
                self.line_valid_count.eq(0),
                self.frame_valid_count.eq(0),
            ]

        with m.If(self.ctrl_valid):
            m.d.sync += self.ctrl_value.eq(self.ctrl_lane)

        with m.If(self.ctrl_lane[0] & self.ctrl_valid):
            m.d.sync += self.data_valid_count.eq(self.data_valid_count + 1)
        with m.If(self.ctrl_lane[1] & self.ctrl_valid):
            m.d.sync += self.line_valid_count.eq(self.line_valid_count + 1)
        with m.If(self.ctrl_lane[2] & self.ctrl_valid):
            m.d.sync += self.frame_valid_count.eq(self.frame_valid_count + 1)

        frame_valid = Signal()
        last_frame_valid = Signal()
        m.d.sync += [
            frame_valid.eq(self.ctrl_lane[2] & self.ctrl_valid),
            last_frame_valid.eq(frame_valid),
        ]
        m.d.comb += self.frame_trigger.eq(~last_frame_valid & frame_valid)

        return m

class Top(Elaboratable):
    def __init__(self):
        self.sensor_reset = ControlSignal()
        self.frame_req = PulseReg(1)

    def elaborate(self, platform: BetaPlatform):
        m = Module()

        m.submodules += self.frame_req

        platform.ps7.fck_domain(requested_frequency=100e6)

        sensor = platform.request("sensor")
        platform.ps7.fck_domain(250e6, "sensor_clk")
        m.d.comb += sensor.lvds_clk.eq(ClockSignal("sensor_clk"))
        m.d.comb += sensor.reset.eq(self.sensor_reset)

        m.d.comb += [
            sensor.frame_req.eq(self.frame_req.pulse),
            sensor.t_exp1.eq(0),
            sensor.t_exp2.eq(0),
        ]

        m.submodules.sensor_spi = Cmv12kSpi(platform.request("sensor_spi"))
        sensor_rx = m.submodules.sensor_rx = Cmv12kRx(sensor)
        stats = m.submodules.stats = DomainRenamer("cmv12k_hword")(Stats())
        trig_sync = m.submodules.trig_sync = PulseSynchronizer(platform.csr_domain, "cmv12k_hword")

        m.d.comb += [
            stats.ctrl_lane.eq(sensor_rx.phy.output[-1]),
            stats.ctrl_valid.eq(sensor_rx.phy.output_valid),
            trig_sync.i.eq(self.frame_req.pulse),
        ]

        add_ila(platform, trace_length=2048, domain="cmv12k_hword", after_trigger=2048-512)
        probe(m, sensor_rx.phy.output_valid, name="output_valid")
        for lane in range(32):
           probe(m, sensor_rx.phy.output[lane], name=f"lane_{lane:02d}")
        probe(m, sensor_rx.phy.output[-1], name="lane_ctrl")
        trigger(m, stats.frame_trigger)

        return m

    @driver_method
    def capture_pattern(self):
        print("training link...")
        self.sensor_rx.configure_sensor_defaults(self.sensor_spi)
        self.sensor_rx.trainer.train(self.sensor_spi)

        print("capturing pattern...")
        self.sensor_spi.enable_test_pattern(True)
        self.stats.reset = 1
        self.ila.reset = 1
        self.frame_req = 1
        print(self.stats.__repr__(allow_recursive=True))

        print("downloading pattern...")
        pattern = list(self.ila.get_values())

        return pattern

if __name__ == "__main__":
    cli(Top, runs_on=(BetaPlatform, ), possible_socs=(ZynqSocPlatform, ))
