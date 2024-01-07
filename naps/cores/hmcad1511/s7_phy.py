from amaranth import *
from amaranth.lib.cdc import PulseSynchronizer

from naps import *
from naps.vendor.xilinx_s7.io import IDelayCtrl, _IDelay, _ISerdes
from naps.cores.debug import ClockDebug
from .spi import HMCAD1511SPI

class HMCAD1511Phy(Elaboratable):
    """A receiver for the HMCAD1511 serial bitstream
    """

    def __init__(self):
        self.reset = ControlSignal()
        self.power_down = ControlSignal()

        self.output = BasicStream(64)

    def elaborate(self, platform):
        m = Module()

        self.spi = m.submodules.spi = HMCAD1511SPI()
        m.submodules.bit_clk = ClockDebug("bit_clk")
        m.submodules.frame_clk = ClockDebug("frame_clk")
        m.submodules.output_clk = ClockDebug("output_clk")

        adc = platform.request("hmcad1511")
        m.d.comb += adc.reset.o.eq(self.reset)
        m.d.comb += adc.power_down.o.eq(self.power_down)

        m.domains.bit_clk = ClockDomain(local=True)
        m.d.comb += ClockSignal("bit_clk").eq(adc.lclk.i)

        m.domains.frame_clk = ClockDomain(local=True)
        m.d.comb += ClockSignal("frame_clk").eq(adc.fclk.i)

        platform.ps7.fck_domain(62.5e6, "output_clk")
        m.d.comb += adc.clk.o.eq(ClockSignal("output_clk"))

        platform.ps7.fck_domain(200e6, "delay_ref")
        m.submodules.delay_ctrl = IDelayCtrl("delay_ref")

        for i, input_slice in enumerate(adc.d.i):
            lane = Signal()
            m.d.comb += lane.eq(input_slice)
            lane = m.submodules[f"lane_{i}"] = HMCAD1511Lane(lane)
            m.d.comb += self.output.payload[i*8:(i+1)*8].eq(lane.output)

        m.d.comb += self.output.valid.eq(1)

        return m
    
    @driver_method
    def init(self):
        self.reset = 1
        self.reset = 0
        self.power_down = 1
        self.power_down = 0

        self.spi.set_test_pattern("sync")
        for i in range(8):
            lane = getattr(self, f"lane_{i}")
            print(f"training lane {i}...")
            lane.train()

class HMCAD1511Lane(Elaboratable):
    def __init__(self, input: Signal):
        self.input = input

        self.delay = ControlSignal(5)
        self.load = ControlSignal()
        self.bitslip = PulseReg(1)

        self.output = Signal(8)


    def elaborate(self, platform):
        m = Module()

        after_delay = Signal()
        idelay = m.submodules.idelay = _IDelay(
            delay_src="iDataIn",
            signal_pattern="data",
            cinvctrl_sel=False,
            high_performance_mode=True,
            refclk_frequency=200.0,
            pipe_sel=False,
            idelay_type="var_load",
            idelay_value=0,
        )
        m.d.comb += [
            idelay.c.eq(ClockSignal()), # control clock
            idelay.ld.eq(self.load), # load value of 0
            idelay.cntvaluein.eq(self.delay),

            idelay.idatain.eq(self.input),
            after_delay.eq(idelay.dataout),
        ]

        bitslip_syncronizer = PulseSynchronizer(platform.csr_domain, "frame_clk")
        m.submodules += [self.bitslip, bitslip_syncronizer]
        m.d.comb += bitslip_syncronizer.i.eq(self.bitslip.pulse)

        iserdes = m.submodules.iserdes = _ISerdes(
            data_width=8,
            data_rate="ddr",
            serdes_mode="master",
            interface_type="networking",
            num_ce=1,
            iobDelay="ifd",
        )

        m.d.comb += [
            iserdes.ddly.eq(after_delay),
            iserdes.ce[1].eq(1),
            iserdes.clk.eq(ClockSignal("bit_clk")),
            iserdes.clkb.eq(~ClockSignal("bit_clk")),
            iserdes.rst.eq(ResetSignal("frame_clk")),
            iserdes.clkdiv.eq(ClockSignal("frame_clk")),
            self.output.eq(Cat(iserdes.q[i] for i in range(1, 9))[::-1]),
            iserdes.bitslip.eq(bitslip_syncronizer.o), # synchronous to frame_clk
        ]

        self.pattern_match_counter = m.submodules.pattern_match_counter = PatternMatchCounter(self.output)

        return m

    @driver_method
    def train(self, timeout=20):
        for _ in range(timeout):
            if self.pattern_match_counter.current == 0b11110000:
                return
            self.bitslip = 1
        raise TimeoutError("lane did not train")


class PatternMatchCounter(Elaboratable):
    def __init__(self, input: Signal):
        self.input = input

        self.current = StatusSignal(len(input))
        self.pattern = ControlSignal(len(input))
        self.reset = PulseReg(1)

        self.match_count = StatusSignal(32)
        self.mismatch_count = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.current.eq(self.input)

        with m.If(self.input == self.pattern):
            m.d.sync += self.match_count.eq(self.match_count + 1)
        with m.Else():
            m.d.sync += self.mismatch_count.eq(self.mismatch_count + 1)

        m.submodules += self.reset
        with m.If(self.reset.pulse):
            m.d.sync += [
                self.match_count.eq(0),
                self.mismatch_count.eq(0)
            ]

        return m