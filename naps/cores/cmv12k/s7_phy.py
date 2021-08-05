from nmigen import *
from nmigen.lib.cdc import PulseSynchronizer

from naps import PulseReg, StatusSignal, ControlSignal, driver_method
from naps.vendor.xilinx_s7 import Mmcm
from naps.vendor.xilinx_s7.io import IDelayCtrl, _IDelay, _ISerdes

class HostTrainer(Elaboratable):
    def __init__(self, num_lanes, bits):
        assert num_lanes <= 32 # the pulse registers cannot be made wider
        assert bits == 12 # patterns, bitslip counts, and validation need adjusting
        self.num_lanes = num_lanes
        self.bits = bits

        self.lane_pattern = ControlSignal(bits)

        # registers accessed by host
        self.data_lane_delay_reset = PulseReg(num_lanes)
        self.data_lane_delay_inc = PulseReg(num_lanes)
        self.data_lane_bitslip = PulseReg(num_lanes)
        self.data_lane_match = StatusSignal(num_lanes)
        self.data_lane_mismatch = StatusSignal(num_lanes)

        self.ctrl_lane_delay_reset = PulseReg(2) # control and clock
        self.ctrl_lane_delay_inc = PulseReg(2)
        self.ctrl_lane_bitslip = PulseReg(2)
        self.ctrl_lane_match = StatusSignal(1)
        self.ctrl_lane_mismatch = StatusSignal(1)

        # signals to/from PHY
        self.lane_delay_reset = Signal(num_lanes+1)
        self.lane_delay_inc = Signal(num_lanes+1)
        self.lane_bitslip = Signal(num_lanes+1)

        self.outclk_delay_reset = Signal()
        self.outclk_delay_inc = Signal()
        self.halfslip = Signal()

        self.lane_match = Signal(num_lanes+1)
        self.lane_mismatch = Signal(num_lanes+1)

    def elaborate(self, platform):
        m = Module()

        m.submodules += [
            self.data_lane_delay_reset,
            self.data_lane_delay_inc,
            self.data_lane_bitslip,
            self.ctrl_lane_delay_reset,
            self.ctrl_lane_delay_inc,
            self.ctrl_lane_bitslip,
        ]

        m.d.comb += [
            self.lane_delay_reset.eq(Cat(self.data_lane_delay_reset.pulse, self.ctrl_lane_delay_reset.pulse[0])),
            self.lane_delay_inc.eq(Cat(self.data_lane_delay_inc.pulse, self.ctrl_lane_delay_inc.pulse[0])),
            self.lane_bitslip.eq(Cat(self.data_lane_bitslip.pulse, self.ctrl_lane_bitslip.pulse[0])),

            self.outclk_delay_reset.eq(self.ctrl_lane_delay_reset.pulse[1]),
            self.outclk_delay_inc.eq(self.ctrl_lane_delay_inc.pulse[1]),
            self.halfslip.eq(self.ctrl_lane_bitslip.pulse[1]),

            self.data_lane_match.eq(self.lane_match[:-1]),
            self.ctrl_lane_match.eq(self.lane_match[-1]),
            self.data_lane_mismatch.eq(self.lane_mismatch[:-1]),
            self.ctrl_lane_mismatch.eq(self.lane_mismatch[-1]),
        ]

        return m

    @driver_method
    def train(self, sensor_spi):
        # set default train pattern
        sensor_spi.set_train_pattern(0b101010_010101)
        self.lane_pattern = 0b101010_010101

        self.set_clock_delay(16) # set clock delay to middle position

        print("control lane initial alignment...")
        if self.initial_alignment():
            print("success!")
        else:
            print("failure!")
            return False

        # align all the lanes with the clock delay set to the middle
        print("initial data alignment...")
        mean_delay = self.data_alignment()
        print(f"mean delay is {mean_delay}")

        # clock delay goes in the opposite direction of the data delay, so set
        # the clock delay to a value that moves the average data delay to the
        # middle to ensure we get the best delay values for the most lanes
        clock_delay = max(0, min(31, 32-mean_delay))
        print(f"configure clock delay to {clock_delay}")
        self.set_clock_delay(clock_delay)

        # now realign all the lanes with the optimal clock delay
        print("data realignment...")
        mean_delay = self.data_alignment()
        print(f"mean delay is now {mean_delay}")

        # make sure a variety of values can be received
        print("validation...")
        valid_channels = self.validate(sensor_spi)
        print(f"working channel mask: 0x{valid_channels:08X}")

        return valid_channels == 0xFFFFFFFF

    @driver_method
    def set_clock_delay(self, delay):
        self.ctrl_lane_delay_reset = 2 # zero clock delay
        while delay > 0:
            self.ctrl_lane_delay_inc = 2 # increment clock delay
            delay -= 1

    @driver_method
    def initial_alignment(self):
        # try all possible options to align the control lane

        for half in range(2):
            for slip in range(6):
                self.ctrl_lane_delay_reset = 1 # zero control lane delay
                for delay in range(32):
                    if self.ctrl_lane_match:
                        return True
                    self.ctrl_lane_delay_inc = 1 # bump control lane delay
                self.ctrl_lane_bitslip = 1 # slip control lane by one bit
            self.ctrl_lane_bitslip = 2 # slip data half words

        return False

    @driver_method
    def data_alignment(self):
        import bitarray.util
        num_lanes = self.num_lanes

        # determine the best bitslip as the one which matches over the most delays
        best_bitslip = [0]*(num_lanes+1)
        best_bitslip_matches = [0]*(num_lanes+1)
        for bitslip in range(6):
            match_count = [0]*(num_lanes+1)
            self.data_lane_delay_reset = (1<<num_lanes)-1 # zero all lane delays
            self.ctrl_lane_delay_reset = 1
            for lane_delay in range(32):
                all_matches = self.data_lane_match | (self.ctrl_lane_match << num_lanes)
                for lane in range(num_lanes+1):
                    match_count[lane] += 1 if all_matches & (1 << lane) else 0
                self.data_lane_delay_inc = (1<<num_lanes)-1 # increment all delays
                self.ctrl_lane_delay_inc = 1
            for lane in range(num_lanes+1):
                if best_bitslip_matches[lane] < match_count[lane]:
                    best_bitslip_matches[lane] = match_count[lane]
                    best_bitslip[lane] = bitslip
            self.data_lane_bitslip = (1<<num_lanes)-1 # slip all bits
            self.ctrl_lane_bitslip = 1

        # apply the determined bitslip to all the channels
        for bitslip in range(6):
            apply_mask = 0
            for lane in range(num_lanes):
                if best_bitslip[lane] > 0:
                    apply_mask |= (1 << lane)
                    best_bitslip[lane] -= 1
            self.data_lane_bitslip = apply_mask
            if best_bitslip[num_lanes] > 0:
                self.ctrl_lane_bitslip = 1
                best_bitslip[num_lanes] -= 1

        # measure the delay window for all the channels to determine the final delay.
        # the window has a 1 bit for each delay tap value which matches properly
        delay_window = [bitarray.util.zeros(32) for _ in range(num_lanes+1)]
        self.data_lane_delay_reset = (1<<num_lanes)-1 # zero all lane delays
        self.ctrl_lane_delay_reset = 1
        for delay in range(32):
            all_matches = self.data_lane_match | (self.ctrl_lane_match << num_lanes)
            for lane in range(num_lanes+1):
                delay_window[lane][delay] = bool(all_matches & (1 << lane))
            self.data_lane_delay_inc = (1<<num_lanes)-1 # increment all delays
            self.ctrl_lane_delay_inc = 1

        best_delay = [None]*(num_lanes+1)
        applied_delay = [0]*(num_lanes+1)
        print("lane 0                             31 delay")
        for lane, window in enumerate(delay_window):
            # the bit period is about 51 delay tap times, and we assume the
            # window of delays that work is 32 taps wide. we thus want to select
            # the delay which is closest to the middle of the window. of course
            # we cannot necessarily see the whole window because we can only
            # delay a maximum of 32 taps
            if window.all(): # all delays work
                best_delay[lane] = 16 # so pick the middle
            elif window.any(): # at least one delay works
                min_border = window.index(window[0]^1) # edges of the window
                max_border = 32-window[::-1].index(window[-1]^1)
                if window[0] and not window[-1]: # e.g. 0x000003FF -> -6
                    best_delay[lane] = min_border - 16
                elif window[-1] and not window[0]: # e.g. 0xFFFC0000 -> 34
                    best_delay[lane] = max_border + 16
                elif not (window[0] or window[-1]): # e.g. 0x007FFFC0 -> 14
                    best_delay[lane] = (max_border + min_border)//2
                else: # e.g. 0xFFFC0003 -> 34
                    best_delay[lane] = min_border - 16 if min_border > (32-max_border) else max_border + 16

            # choose tap closest to a delay that actually exists
            applied_delay[lane] = max(0, min(31, best_delay[lane] or 0))
            print(f"[{lane:02d}] {window.to01()} => {applied_delay[lane]:02d}")

        # apply all the delays
        self.data_lane_delay_reset = (1<<num_lanes)-1 # zero all lane delays
        self.ctrl_lane_delay_reset = 1
        for delay in range(32):
            apply_mask = 0
            for lane in range(num_lanes):
                if applied_delay[lane] > 0:
                    apply_mask |= (1 << lane)
                    applied_delay[lane] -= 1
            self.data_lane_delay_inc = apply_mask
            if applied_delay[num_lanes] > 0:
                self.ctrl_lane_delay_inc = 1
                applied_delay[num_lanes] -= 1

        # return mean of valid delays, used for determining optimal clock delay
        valid_delays = [delay for delay in best_delay if delay is not None]
        if len(valid_delays) == 0: return 16
        return int(sum(valid_delays)/len(valid_delays))

    @driver_method
    def validate(self, sensor_spi):
        num_lanes = self.num_lanes

        if not self.ctrl_lane_match: return 0 # control lane has fixed pattern

        # try all patterns with each bit exclusively set and clear
        valid_channels = (1<<num_lanes)-1
        for bit in range(12):
            sensor_spi.set_train_pattern(1 << bit) # tell sensor to transmit pattern
            self.lane_pattern = 1 << bit # set matcher to expect pattern
            valid_channels &= self.data_lane_match

            sensor_spi.set_train_pattern((1 << bit)^0xFFF)
            self.lane_pattern = (1 << bit)^0xFFF
            valid_channels &= self.data_lane_match

        return valid_channels


class IDelayIncremental(Elaboratable):
    def __init__(self, signal_pattern="data"):
        self.signal_pattern = signal_pattern # "data" or "clock"

        self.input = Signal()

        # synchronous to "sync" domain
        self.reset = Signal() # set delay to 0
        self.step = Signal() # apply below change
        self.inc = Signal(reset=1) # 1 = add 1 to delay, 0 = subtract 1 from delay

        self.output = Signal()

    def elaborate(self, platform):
        m = Module()

        idelay = m.submodules.idelay = _IDelay(
            delay_src="iDataIn",
            signal_pattern=self.signal_pattern,
            cinvctrl_sel=False,
            high_performance_mode=True,
            refclk_frequency=200.0,
            pipe_sel=False,
            idelay_type="variable",
            idelay_value=0,
        )
        m.d.comb += [
            idelay.c.eq(ClockSignal()), # control clock
            idelay.ld.eq(self.reset), # load value of 0
            idelay.ce.eq(self.step),
            idelay.inc.eq(self.inc),

            idelay.idatain.eq(self.input),
            self.output.eq(idelay.dataout),
        ]

        return m

class ISerdes(Elaboratable):
    def __init__(self, ser_domain, par_domain="sync"):
        self.ser_domain = ser_domain
        self.par_domain = par_domain

        self.input = Signal() # synchronous to ser_domain
        self.bitslip = Signal() # synchronous to par_domain
        self.output = Signal(6) # synchronous to par_domain

    def elaborate(self, platform):
        m = Module()

        iserdes = m.submodules.iserdes = _ISerdes(
            data_width=6,
            data_rate="sdr",
            serdes_mode="master",
            interface_type="networking",
            num_ce=1,
            iobDelay="ifd",
        )

        m.d.comb += [
            iserdes.ddly.eq(self.input),
            iserdes.ce[1].eq(1),
            iserdes.clk.eq(ClockSignal(self.ser_domain)),
            iserdes.clkb.eq(~ClockSignal(self.ser_domain)),
            iserdes.rst.eq(ResetSignal(self.par_domain)),
            iserdes.clkdiv.eq(ClockSignal(self.par_domain)),
            self.output.eq(Cat(iserdes.q[i] for i in range(1, 7))[::-1]),
            iserdes.bitslip.eq(self.bitslip),
        ]

        return m

class MatchMonitor(Elaboratable):
    def __init__(self, bits):
        self.input = Signal(bits)
        self.input_valid = Signal()
        self.pattern = Signal(bits)

        self.match = Signal()
        self.mismatch = Signal()

    def elaborate(self, platform):
        m = Module()

        matched = Signal(8)
        with m.If(self.input_valid):
            m.d.sync += [
                matched.eq(Cat(self.input == self.pattern, matched)),
                self.match.eq(matched == 0xFF),
                self.mismatch.eq(matched == 0x00),
            ]

        return m

class Cmv12kPhy(Elaboratable):
    def __init__(self, num_lanes, bits, freq, mode, domain="cmv12k"):
        assert bits == 12 # SERDESes need adjusting
        assert freq == 250e6 # PLL configuration needs adjusting
        assert mode == "normal" # do other modes need adjusting...?
        self.bits = bits
        self.freq = freq
        self.mode = mode
        self.domain = domain
        # derived domains:
        # cmv12k_in: sensor's 125MHz DDR bit clock, synchronous to lane input, from delay
        # cmv12k_bit: 250MHz bit clock, from PLL
        # cmv12k_hword: 41.7MHz half-word clock, synchronous to output, from PLL
        # cmv12k_ctrl: 10MHz or so AXI clock, synchronous to control input, externally provided
        # cmv12k_delay_ref: 200MHz delay module reference, externally provided

        # signal inputs
        self.outclk = Signal()
        self.lanes = Signal(num_lanes+1) # control lane is top lane

        # signal outputs
        self.output = [Signal(bits) for _ in range(num_lanes+1)]
        self.output_valid = Signal() # every other cycle

        # control inputs
        self.lane_pattern = Signal(bits) # except for control lane
        self.lane_delay_reset = Signal(num_lanes+1) # reset delay value to 0
        self.lane_delay_inc = Signal(num_lanes+1) # increment delay count by 1
        self.lane_bitslip = Signal(num_lanes+1) # slip serdes by one bit

        self.outclk_delay_reset = Signal()
        self.outclk_delay_inc = Signal()
        self.halfslip = Signal() # slip serdes by one half-word

        # control outputs
        self.lane_match = Signal(num_lanes+1)
        self.lane_mismatch = Signal(num_lanes+1)

    def elaborate(self, platform):
        m = Module()

        dom_in = self.domain+"_in"
        dom_bit = self.domain+"_bit"
        dom_hword = self.domain+"_hword"
        dom_ctrl = self.domain+"_ctrl"

        # set up the delay module for the input clock
        m.submodules.delay_ctrl = IDelayCtrl("cmv12k_delay_ref")

        delay_clk = m.submodules.delay_clk = DomainRenamer(dom_ctrl)(IDelayIncremental("clock"))
        m.domains += ClockDomain(self.domain+"_in")
        m.d.comb += [
            delay_clk.reset.eq(self.outclk_delay_reset),
            delay_clk.step.eq(self.outclk_delay_inc),

            delay_clk.input.eq(self.outclk),
            ClockSignal(self.domain+"_in").eq(delay_clk.output),
        ]

        # generate the derived clocks with a PLL
        pll = m.submodules.pll = Mmcm(125e6, 6, 1, input_domain=self.domain+"_in")
        pll.output_domain(dom_bit, 3)
        pll.output_domain(dom_hword, 18)

        halfslip_sync = m.submodules.halfslip_sync = PulseSynchronizer(dom_ctrl, dom_hword)
        m.d.comb += halfslip_sync.i.eq(self.halfslip)
        with m.If(~halfslip_sync.o):
            # output is valid every other half-word. if slipping, write to the
            # same half-word position as last cycle
            m.d[dom_hword] += self.output_valid.eq(~self.output_valid)

        for lane in range(len(self.lanes)):
            delay_lane = m.submodules["delay_lane_"+str(lane)] = DomainRenamer(dom_ctrl)(IDelayIncremental())
            m.d.comb += [
                delay_lane.reset.eq(self.lane_delay_reset[lane]),
                delay_lane.step.eq(self.lane_delay_inc[lane]),

                delay_lane.input.eq(self.lanes[lane]),
            ]

            iserdes = m.submodules["iserdes_"+str(lane)] = ISerdes(dom_bit, dom_hword)
            bitslip_sync = m.submodules["bitslip_sync_"+str(lane)] = PulseSynchronizer(dom_ctrl, dom_hword)
            m.d.comb += [
                iserdes.input.eq(delay_lane.output),

                bitslip_sync.i.eq(self.lane_bitslip[lane]),
                iserdes.bitslip.eq(bitslip_sync.o),
            ]

            with m.If(self.output_valid): # low bits come in first
                m.d[dom_hword] += self.output[lane][0:6].eq(iserdes.output)
            with m.Else():
                m.d[dom_hword] += self.output[lane][6:12].eq(iserdes.output)

            monitor = m.submodules["monitor_"+str(lane)] = DomainRenamer(dom_hword)(MatchMonitor(self.bits))
            m.d.comb += [
                monitor.input.eq(self.output[lane]),
                monitor.input_valid.eq(self.output_valid),
                monitor.pattern.eq(self.lane_pattern),

                self.lane_match[lane].eq(monitor.match),
                self.lane_mismatch[lane].eq(monitor.mismatch),
            ]

            if lane == len(self.lanes)-1: # control lane has fixed pattern
                m.d.comb += monitor.pattern.eq(0x080)

        return m
