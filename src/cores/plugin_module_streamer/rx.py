from functools import reduce

from nmigen import *
from nmigen.hdl.ast import Rose

from cores.csr_bank import StatusSignal
from cores.primitives.lattice_machxo2.clocking import Pll, EClkSync, ClkDiv
from util.stream import StreamEndpoint


class PluginModuleStreamerRx(Elaboratable):
    def __init__(self, plugin):
        """
        This module needs to run in the word clock domain of the bus.
        """
        self.plugin = plugin
        self.output = StreamEndpoint(32, is_sink=False, has_last=False)

        self.ready = StatusSignal()

    def elaborate(self, platform):
        m = Module()

        m.domains += ClockDomain("wclk_in")
        m.d.comb += ClockSignal("wclk_in").eq(self.plugin.clk_word)

        pll = m.submodules.pll = Pll(50e6, 4, 1, "wclk_in")
        pll.output_domain("ddr_domain", 1)

        m.submodules.eclk_ddr = EClkSync("ddr_domain", "ddr_domain_eclk")
        m.submodules.clk_div_half = ClkDiv("ddr_domain_eclk", "ddr_domain_x1_1", "word_x2", div=2)
        m.submodules.clk_div_quater = ClkDiv("ddr_domain_eclk", "ddr_domain_x1_2", "sync", div=4)

        lanes = []
        for i in range(4):
            lane = m.submodules["lane{}".format(i)] = LaneAligner(
                i=self.plugin["lvds{}".format(i)],
                in_testpattern_mode=~self.output.valid,
                ddr_domain="ddr_domain_eclk",
                word_x2_domain="word_x2",
            )
            lanes.append(lane)

        m.d.sync += self.output.valid.eq(self.plugin.valid)
        m.d.sync += self.output.payload.eq(Cat(*[lane.output for lane in lanes]))
        m.d.comb += self.ready.eq(
            self.output.ready & (
                reduce(lambda a, b: a & b, [
                    lane.word_aligned & lane.bit_aligned for lane in lanes
                ])
            )
        )

        return m


class LaneAligner(Elaboratable):
    def __init__(self, i, in_testpattern_mode, ddr_domain, word_x2_domain, testpattern=0b00000110):
        """
        Does bit and lane alignment of one lane usig a given testpattern if in_testpattern_mode is high
        """
        self.i = i
        self.in_testpattern_mode = in_testpattern_mode
        self.testpattern = testpattern
        self.word_x2_domain = word_x2_domain
        self.ddr_domain = ddr_domain

        self.output = Signal(8)
        self.bit_aligned = StatusSignal()
        self.word_aligned = StatusSignal()

        self.bitslips = StatusSignal(32)
        self.delay = StatusSignal(5)
        self.error = StatusSignal()

    def elaborate(self, platform):
        m = Module()

        delayed = Signal()
        m.submodules.delayd = Instance(
            "DELAYD",

            i_A=self.i,
            i_DEL0=self.delay[0],
            i_DEL1=self.delay[1],
            i_DEL2=self.delay[2],
            i_DEL3=self.delay[3],
            i_DEL4=self.delay[4],

            o_Z=delayed,
        )

        iserdes = m.submodules.iserdes = FakeX8ISerdes(delayed, self.ddr_domain, self.word_x2_domain)

        with m.If(self.in_testpattern_mode):
            with m.FSM():
                last_captured_word = Signal(8)
                with m.State("INITIAL"):
                    m.d.sync += last_captured_word.eq(self.output)
                    m.next = "ALIGN_BIT"

                with m.State("ALIGN_BIT"):
                    start_longest = Signal.like(self.delay)
                    len_longest = Signal.like(self.delay)
                    start_current = Signal.like(self.delay)

                    m.d.sync += last_captured_word.eq(self.output)

                    with m.If((self.output != last_captured_word) | (self.delay == ((2 ** len(self.delay)) - 1))):
                        m.d.sync += start_current.eq(self.delay)
                        len_current = (self.delay - start_current)
                        with m.If(len_current > len_longest):
                            m.d.sync += len_longest.eq(len_current)
                            m.d.sync += start_longest.eq(start_current)

                    with m.If(self.delay < 2 ** len(self.delay)):
                        m.d.sync += self.delay.eq(self.delay + 1)
                    with m.Else():
                        m.d.sync += self.delay.eq(start_longest + (len_longest >> 1))
                        m.d.sync += self.bit_aligned.eq(1)
                        m.next = "ALIGN_WORD"

                with m.State("ALIGN_WORD"):
                    with m.If(self.output != self.testpattern):
                        m.d.comb += iserdes.bitslip.eq(1)
                        m.next = "ALIGN_WORD"
                    with m.Else():
                        m.d.sync += self.word_aligned.eq(1)
                        m.next = "ALIGNED"

                with m.State("ALIGNED"):
                    with m.If(self.output != self.testpattern):
                        m.d.sync += self.error.eq(1)
                        # TODO: retrain if this is the case after we finished basic debugging

        return m


class FakeX8ISerdes(Elaboratable):
    def __init__(self, input, ddr_domain, word_x2_domain):
        self.input = input
        self.output = Signal(8)
        self.bitslip = Signal()

        self.word_x2_domain = word_x2_domain
        self.ddr_domain = ddr_domain

    def elaborate(self, platform):
        m = Module()

        serdes_output = Signal(4)
        real_bitslip = Signal()

        bitslip = Rose(self.bitslip, domain=self.word_x2_domain)

        with m.If(bitslip):
            m.d[self.word_x2_domain] += real_bitslip.eq(~real_bitslip)

        lower_upper = Signal()
        with m.If(bitslip & ~real_bitslip):
            m.d[self.word_x2_domain] += lower_upper.eq(lower_upper)
        with m.Else():
            m.d[self.word_x2_domain] += lower_upper.eq(~lower_upper)

        with m.If(lower_upper):
            m.d[self.word_x2_domain] += self.output[0:4].eq(serdes_output)
        with m.Else():
            m.d[self.word_x2_domain] += self.output[4:8].eq(serdes_output)

        m.submodules.iddr = Instance(
            "IDDRX2E",

            i_D=self.input,
            i_ECLK=ClockSignal(self.ddr_domain),
            i_SCLK=ClockSignal(),
            i_RST=ResetSignal(),
            i_ALIGNWD=(bitslip & real_bitslip),

            o_Q0=serdes_output[0],
            o_Q1=serdes_output[1],
            o_Q2=serdes_output[2],
            o_Q3=serdes_output[3],
        )

        return m
