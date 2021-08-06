# set up and demonstrate capturing the test pattern of CMV12k

# DEMO PROCEDURE:
# 1. build the fatbitstream with `python3 applets/cmv12k/pattern_test.py -b`
# 2. copy the resulting build/pattern_test_*/pattern_test.zip file to the Beta
# 3. log into the Beta and get root access with e.g. `sudo su`
# 4. power up the sensor with `axiom_power_init.sh && axiom_power_on.sh`
# 5. load the fatbitstream with `./pattern_test.zip --run`
# 6. run `pattern = design.capture_pattern()` function at the prompt

from nmigen import *
from nmigen.lib.cdc import FFSynchronizer, PulseSynchronizer
from naps import *

class Stats(Elaboratable):
    def __init__(self):
        self.pixel_valid_count = StatusSignal(32)
        self.line_valid_count = StatusSignal(32)
        self.frame_valid_count = StatusSignal(32)

        self.pixel_rose_count = StatusSignal(32)
        self.line_rose_count = StatusSignal(32)
        self.frame_rose_count = StatusSignal(32)

        self.ctrl_value = StatusSignal(12)
        self.reset = PulseReg(1)

        self.ctrl_lane = Signal(12)
        self.ctrl_valid = Signal()

        self.frame_start_trigger = Signal()
        self.frame_end_trigger = Signal()

    def elaborate(self, platform):
        m = Module()

        m.submodules += self.reset

        reset_sync = m.submodules.reset_sync = PulseSynchronizer(platform.csr_domain, "sync")
        m.d.comb += reset_sync.i.eq(self.reset.pulse)

        with m.If(reset_sync.o):
            m.d.sync += [
                self.pixel_valid_count.eq(0),
                self.line_valid_count.eq(0),
                self.frame_valid_count.eq(0),

                self.pixel_rose_count.eq(0),
                self.line_rose_count.eq(0),
                self.frame_rose_count.eq(0),
            ]

        prev_ctrl = Signal(12)
        m.d.sync += self.ctrl_value.eq(prev_ctrl)
        with m.If(self.ctrl_valid):
            m.d.sync += prev_ctrl.eq(self.ctrl_lane)

            with m.If(self.ctrl_lane[0]):
                m.d.sync += self.pixel_valid_count.eq(self.pixel_valid_count + 1)
            with m.If(self.ctrl_lane[1]):
                m.d.sync += self.line_valid_count.eq(self.line_valid_count + 1)
            with m.If(self.ctrl_lane[2]):
                m.d.sync += self.frame_valid_count.eq(self.frame_valid_count + 1)

            with m.If(~prev_ctrl[0] & self.ctrl_lane[0]):
                m.d.sync += self.pixel_rose_count.eq(self.pixel_rose_count + 1)
            with m.If(~prev_ctrl[1] & self.ctrl_lane[1]):
                m.d.sync += self.line_rose_count.eq(self.line_rose_count + 1)
            with m.If(~prev_ctrl[2] & self.ctrl_lane[2]):
                m.d.sync += self.frame_rose_count.eq(self.frame_rose_count + 1)
                m.d.comb += self.frame_start_trigger.eq(1)
            with m.If(prev_ctrl[2] & ~self.ctrl_lane[2]):
                m.d.comb += self.frame_end_trigger.eq(1)

        return m

class Top(Elaboratable):
    def __init__(self):
        self.sensor_reset = ControlSignal()
        self.frame_req = PulseReg(1)
        self.capture_pattern_end = ControlSignal()

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

        m.d.comb += [
            stats.ctrl_lane.eq(sensor_rx.phy.output[-1]),
            stats.ctrl_valid.eq(sensor_rx.phy.output_valid),
        ]

        add_ila(platform, trace_length=2048, domain="cmv12k_hword", after_trigger=2048-768)
        probe(m, sensor_rx.phy.output_valid, name="output_valid")
        for lane in range(32):
           probe(m, sensor_rx.phy.output[lane], name=f"lane_{lane:02d}")
        probe(m, sensor_rx.phy.output[-1], name="lane_ctrl")

        capture_pattern_end = Signal()
        m.submodules += FFSynchronizer(self.capture_pattern_end, capture_pattern_end)
        trigger(m, Mux(capture_pattern_end, stats.frame_end_trigger, stats.frame_start_trigger))

        return m

    @driver_method
    def capture_pattern(self):
        import time
        print("training link...")
        self.sensor_rx.configure_sensor_defaults(self.sensor_spi)
        self.sensor_rx.trainer.train(self.sensor_spi)

        # we want to capture the start and end of the training pattern and
        # interpolate the bits in the middle (i.e. replicate the missing lines).
        assert self.sensor_rx.num_lanes == 32
        assert self.sensor_rx.mode == "normal"

        print("capturing pattern start...")
        self.sensor_spi.enable_test_pattern(True)
        self.capture_pattern_end = 0
        self.stats.reset = 1
        self.ila.arm()
        self.frame_req = 1
        time.sleep(0.05)
        print(self.stats.__repr__(allow_recursive=True))
        assert self.stats.pixel_valid_count == (4096*3072/32), "sensor did not output expected number of pixels"

        print("downloading pattern start...")
        pattern = list(self.ila.get_values())

        print("capturing pattern end...")
        self.capture_pattern_end = 1
        self.stats.reset = 1
        self.ila.arm()
        self.frame_req = 1
        time.sleep(0.05)
        assert self.stats.pixel_valid_count == (4096*3072/32), "sensor did not output expected number of pixels"

        print("downloading pattern end...")
        pattern_end = list(self.ila.get_values())

        print("validating pattern...")
        # search for the start of frame trigger, bit 2 of control lane
        i = 0
        while not (pattern[i][0] != 0 and pattern[i][-1] & 4 != 0): i += 1
        pre_frame, pattern = pattern[:i], pattern[i:]
        # search for the start of the next line, bit 1 of control lane
        i = 0
        while not (pattern[i][0] != 0 and pattern[i][-1] & 2 == 0): i += 1
        while not (pattern[i][0] != 0 and pattern[i][-1] & 2 != 0): i += 1
        first_line, pattern = pattern[:i], pattern[i:]
        # search for the start of the third line
        i = 0
        while not (pattern[i][0] != 0 and pattern[i][-1] & 2 == 0): i += 1
        while not (pattern[i][0] != 0 and pattern[i][-1] & 2 != 0): i += 1
        second_line, pattern = pattern[:i], pattern[i:]
        # search for the start of the last line and the end of the pattern
        i = 0
        while not (pattern_end[i][0] != 0 and pattern_end[i][-1] & 2 == 0): i += 1
        while not (pattern_end[i][0] != 0 and pattern_end[i][-1] & 2 != 0): i += 1
        pattern_end = pattern_end[i:]

        assert first_line == second_line, "sensor lines do not match"

        # each lane's value is that lane's number plus the pixel number
        for lane_group in range(2): # pixels come in two groups because we use half the lanes
            lane_values = [*range(lane_group, 32, 2), *range(lane_group, 32, 2)]
            for pixel in range(128): # pixels come in runs of 128
                # 128 pixels + 1 dead time separates groups
                assert first_line[258*lane_group+2*pixel][1:-1] == lane_values
                for x in range(len(lane_values)): lane_values[x] += 1

        # now we can build the whole pattern from the pieces we've captured
        pattern = [tuple(x) for x in pre_frame] # idle time before the first line
        first_line = tuple(tuple(x) for x in first_line)
        for line in range(1535): # each "line" is actually two sensor lines
            pattern.extend(first_line)
        pattern.extend(tuple(x) for x in pattern_end) # last line and subsequent idle time

        # finally, make sure the pattern we built matches the statistics we captured
        pixel_valid_count = 0
        line_valid_count = 0
        frame_valid_count = 0

        pixel_rose_count = 0
        line_rose_count = 0
        frame_rose_count = 0

        prev_ctrl = 0
        for v in pattern:
            if v[0] == 0: continue
            ctrl_lane = v[-1]

            if ctrl_lane & 1: pixel_valid_count += 1
            if ctrl_lane & 2: line_valid_count += 1
            if ctrl_lane & 4: frame_valid_count += 1

            if not (prev_ctrl & 1) and ctrl_lane & 1: pixel_rose_count += 1
            if not (prev_ctrl & 2) and ctrl_lane & 2: line_rose_count += 1
            if not (prev_ctrl & 4) and ctrl_lane & 4: frame_rose_count += 1

            prev_ctrl = ctrl_lane

        assert self.stats.pixel_valid_count == pixel_valid_count
        assert self.stats.line_valid_count == line_valid_count
        assert self.stats.frame_valid_count == frame_valid_count

        assert self.stats.pixel_rose_count == pixel_rose_count
        assert self.stats.line_rose_count == line_rose_count
        assert self.stats.frame_rose_count == frame_rose_count

        print("success!")

        return pattern

if __name__ == "__main__":
    cli(Top, runs_on=(BetaPlatform, ), possible_socs=(ZynqSocPlatform, ))
