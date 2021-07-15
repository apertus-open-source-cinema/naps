from nmigen import *
from nmigen.lib.cdc import PulseSynchronizer

from naps import StatusSignal, ControlSignal, EventReg, Response, driver_method
from naps.vendor.xilinx_s7 import Mmcm
from naps.vendor.xilinx_s7.io import IDelayCtrl, _IDelay, _ISerdes

class PokeReg(EventReg, Elaboratable):
    def __init__(self, bits):
        super().__init__(bits=bits)

        self.poke = Signal(bits)
        self._write_val = Signal(bits)

        def handle_read(m, data, read_done):
            m.d.sync += data.eq(0)
            read_done(Response.OK)

        def handle_write(m, data, write_done):
            m.d.comb += self._write_val.eq(data)
            write_done(Response.OK)

        self.handle_read = handle_read
        self.handle_write = handle_write

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.poke.eq(self._write_val)

        return m

class HostTrainer(Elaboratable):
    def __init__(self, num_lanes):
        self.lane_pattern = ControlSignal(12)

        # registers accessed by host
        self.data_lane_delay_reset = PokeReg(num_lanes)
        self.data_lane_delay_inc = PokeReg(num_lanes)
        self.data_lane_bitslip = PokeReg(num_lanes)
        self.data_lane_match = StatusSignal(num_lanes)
        self.data_lane_mismatch = StatusSignal(num_lanes)

        self.ctrl_lane_delay_reset = PokeReg(2) # control and clock
        self.ctrl_lane_delay_inc = PokeReg(2)
        self.ctrl_lane_bitslip = PokeReg(2)
        self.ctrl_lane_match = StatusSignal(1)
        self.ctrl_lane_mismatch = StatusSignal(1)

        # signals to/from PHY
        self.lane_delay_reset = Signal(num_lanes+1)
        self.lane_delay_inc = Signal(num_lanes+1)
        self.lane_bitslip = Signal(num_lanes+1)

        self.outclk_delay_reset = Signal()
        self.outclk_delay_inc = Signal()
        self.halfswap = Signal()

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
            self.lane_delay_reset.eq(Cat(self.data_lane_delay_reset.poke, self.ctrl_lane_delay_reset.poke[0])),
            self.lane_delay_inc.eq(Cat(self.data_lane_delay_inc.poke, self.ctrl_lane_delay_inc.poke[0])),
            self.lane_bitslip.eq(Cat(self.data_lane_bitslip.poke, self.ctrl_lane_bitslip.poke[0])),

            self.outclk_delay_reset.eq(self.ctrl_lane_delay_reset.poke[1]),
            self.outclk_delay_inc.eq(self.ctrl_lane_delay_inc.poke[1]),
            self.halfswap.eq(self.ctrl_lane_bitslip.poke[1]),

            self.data_lane_match.eq(self.lane_match[:-1]),
            self.ctrl_lane_match.eq(self.lane_match[-1]),
            self.data_lane_mismatch.eq(self.lane_mismatch[:-1]),
            self.ctrl_lane_mismatch.eq(self.lane_mismatch[-1]),
        ]

        return m

    @driver_method
    def set_data_delay(self, lane, delay):
        mask = 1 << lane
        self.data_lane_delay_reset = mask
        while delay > 0:
            self.data_lane_delay_inc = mask
            delay -= 1

    @driver_method
    def set_ctrl_delay(self, lane, delay):
        mask = 1 << lane
        self.ctrl_lane_delay_reset = mask
        while delay > 0:
            self.ctrl_lane_delay_inc = mask
            delay -= 1

    @driver_method
    def data_matching(self, lane):
        mask = 1 << lane
        match = True if self.data_lane_match & mask else False
        mismatch = True if self.data_lane_mismatch & mask else False

        return match and not mismatch

    @driver_method
    def configure_sensor(self, sensor):
        # set default train pattern
        sensor.write_reg(89, 0xA95)
        self.lane_pattern = 0xA95
        # switch (only) sensor sequencer to 12 bit mode
        sensor.write_reg(118, 0)

    @driver_method
    def initial_alignment(self):
        # try to align just the control lane
        self.set_ctrl_delay(1, 16) # set clock delay to middle position

        for half in range(2):
            for slip in range(6):
                self.set_ctrl_delay(0, 0) # zero control lane delay
                for delay in range(32):
                    if self.ctrl_lane_match:
                        return True
                    self.ctrl_lane_delay_inc = 1 # bump control lane delay
                self.ctrl_lane_bitslip = 1 # slip control lane by one bit
            self.ctrl_lane_bitslip = 2 # swap data half words

        return False

    @driver_method
    def clock_alignment(self):
        num_lanes = 32
        self.set_ctrl_delay(1, 0) # zero clock delay

        best_clock_delay = 0
        best_clock_match = 0
        # try out all the possible clock delays
        for clock_delay in range(32):
            # we want the clock delay for which the lanes match the "most" in
            # order to give us the widest latitude for adjustment.

            # first, we evaluate each lane by choosing the bitslip value for
            # which the lane matches over the maximum number of delays
            best_match_count = [0]*num_lanes
            for bitslip in range(6):
                match_count = [0]*num_lanes
                self.data_lane_delay_reset = (1<<num_lanes)-1 # zero all lane delays
                for lane_delay in range(32):
                    all_matches = self.data_lane_match
                    for lane in range(num_lanes):
                        match_count[lane] += 1 if all_matches & (1 << lane) else 0
                    self.data_lane_delay_inc = (1<<num_lanes)-1 # increment all delays
                for lane in range(num_lanes):
                    if best_match_count[lane] < match_count[lane]:
                        best_match_count[lane] = match_count[lane]
                self.data_lane_bitslip = (1<<num_lanes)-1 # slip all bits
            # then we measure the "most"ness for this clock delay as which lane matched the fewest times
            clock_match = min(best_match_count)
            if best_clock_match < clock_match:
                best_clock_match = clock_match
                best_clock_delay = clock_delay

            print("[{:02d}] = {:02d}".format(clock_delay, clock_match))
            self.ctrl_lane_delay_inc = 2

        self.set_ctrl_delay(1, best_clock_delay)
        return best_clock_delay, best_clock_match

    @driver_method
    def data_alignment(self):
        num_lanes = 32

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

        # measure the delay window for all the channels to determine the final delay
        delay_window = [0]*(num_lanes+1)
        self.data_lane_delay_reset = (1<<num_lanes)-1 # zero all lane delays
        self.ctrl_lane_delay_reset = 1
        for delay in range(32):
            all_matches = self.data_lane_match | (self.ctrl_lane_match << num_lanes)
            for lane in range(num_lanes+1):
                delay_window[lane] |= (1 << delay) if all_matches & (1 << lane) else 0
            self.data_lane_delay_inc = (1<<num_lanes)-1 # increment all delays
            self.ctrl_lane_delay_inc = 1

        best_delay = [0]*(num_lanes+1)
        for lane, window in enumerate(delay_window):
            if window == 0xFFFFFFFF: # all delays work
                best_delay[lane] = 16 # so pick the middle
            elif window & 0x80000000: # large delays work but small ones don't
                # take the first delay value that works, then delay 16 more to hit the middle
                lsb = 0
                while not (window & (1 << lsb)): lsb += 1
                best_delay[lane] = min(31, lsb+16)
            elif window != 0: # small delays work but large ones don't
                # take the last delay value that works, then delay 16 less to hit the middle
                msb = 31
                while not (window & (1 << msb)): msb -= 1
                best_delay[lane] = max(0, msb-16)

            print("[{:02d}] 0x{:08X} => {:02d}".format(lane, window, best_delay[lane], best_bitslip[lane]))

        # apply all the delays
        self.data_lane_delay_reset = (1<<num_lanes)-1 # zero all lane delays
        self.ctrl_lane_delay_reset = 1
        for delay in range(32):
            apply_mask = 0
            for lane in range(num_lanes):
                if best_delay[lane] > 0:
                    apply_mask |= (1 << lane)
                    best_delay[lane] -= 1
            self.data_lane_delay_inc = apply_mask
            if best_delay[num_lanes] > 0:
                self.ctrl_lane_delay_inc = 1
                best_delay[num_lanes] -= 1

    @driver_method
    def validate(self, sensor):
        num_lanes = 32

        if not self.ctrl_lane_match: return 0

        valid_channels = (1<<num_lanes)-1
        for bit in range(12):
            sensor.write_reg(89, 1 << bit)
            self.lane_pattern = 1 << bit
            valid_channels &= self.data_lane_match

            sensor.write_reg(89, (1 << bit)^0xFFF)
            self.lane_pattern = (1 << bit)^0xFFF
            valid_channels &= self.data_lane_match

        return valid_channels


class IDelayIncremental(Elaboratable):
    def __init__(self):
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
            signal_pattern="data",
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

class MatchMonitor:
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
    def __init__(self, num_lanes=32, bits=12, domain="cmv12k"):
        assert bits == 12
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
        self.output = [Signal(12) for _ in range(num_lanes+1)]
        self.output_valid = Signal() # every other cycle

        # control inputs
        self.lane_pattern = Signal(12) # except for control lane
        self.lane_delay_reset = Signal(num_lanes+1) # reset delay value to 0
        self.lane_delay_inc = Signal(num_lanes+1) # increment delay count by 1
        self.lane_bitslip = Signal(num_lanes+1) # slip serdes by one bit

        self.outclk_delay_reset = Signal()
        self.outclk_delay_inc = Signal()
        self.halfswap = Signal() # swap order of half-words

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

        delay_clk = m.submodules.delay_clk = DomainRenamer(dom_ctrl)(IDelayIncremental())
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

        halfswap_sync = m.submodules.halfswap_sync = PulseSynchronizer(dom_ctrl, dom_hword)
        curr_halfswap = Signal()
        m.d.comb += halfswap_sync.i.eq(self.halfswap)
        m.d[dom_hword] += [
            self.output_valid.eq(~self.output_valid),
            curr_halfswap.eq(curr_halfswap ^ halfswap_sync.o),
        ]

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

            with m.If(self.output_valid ^ curr_halfswap):
                m.d[dom_hword] += self.output[lane][0:6].eq(iserdes.output)
            with m.Else():
                m.d[dom_hword] += self.output[lane][6:12].eq(iserdes.output)

            monitor = m.submodules["monitor_"+str(lane)] = DomainRenamer(dom_hword)(MatchMonitor(12))
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
