from nmigen import *
from naps import BasicStream, StatusSignal, ControlSignal, driver_method
from naps.cores import InflexibleSourceDebug
from naps.vendor.lattice_machxo2 import ISerdes8, Pll, EClkSync, ClkDiv

__all__ = ["PluginModuleStreamerRx"]


class PluginModuleStreamerRx(Elaboratable):
    def __init__(self, plugin, domain_name="sync"):
        self.plugin = plugin
        self.output = BasicStream(32)
        self.domain_name = domain_name

        self.trained = ControlSignal()
        self.valid = StatusSignal()

    def elaborate(self, platform):
        m = Module()

        domain = self.domain_name
        domain_in = domain + "_in"
        domain_ddr = domain + "_ddr"
        domain_ddr_eclk = domain + "_ddr_eclk"

        m.domains += ClockDomain(domain_in)
        m.d.comb += ClockSignal(domain_in).eq(self.plugin.clk_word)

        pll = m.submodules.pll = Pll(input_freq=50e6, vco_mul=4, vco_div=1, input_domain=domain_in)
        pll.output_domain(domain_ddr, 1)

        m.submodules.eclk_ddr = EClkSync(domain_ddr, domain_ddr_eclk, input_frequency=400e6)

        lanes = []
        bitslip_signal = Signal()
        for i in range(4):
            lane = m.submodules["lane{}".format(i)] = LaneBitAligner(
                input=self.plugin["lvds{}".format(i)],
                in_testpattern_mode=~self.valid,
                bitslip_signal=bitslip_signal,
                ddr_domain=domain_ddr_eclk,
            )
            lanes.append(lane)
        word_aligner = m.submodules.word_aligner = WordAligner(domain_ddr_eclk, lanes[0].output)
        m.d.comb += bitslip_signal.eq(word_aligner.bitslip)

        valid_iserdes = m.submodules.valid_iserdes = ISerdes8(self.plugin.valid, domain_ddr_eclk, word_domain="sync", invert=True)
        m.d.comb += valid_iserdes.bitslip.eq(bitslip_signal)
        m.d.comb += self.valid.eq(valid_iserdes.output[4])

        m.d.sync += self.output.payload.eq(Cat(*[lane.output for lane in lanes]))
        m.d.comb += self.output.valid.eq(
            self.valid & self.trained
        )

        m.submodules.inflexible_output = InflexibleSourceDebug(self.output)

        return DomainRenamer(domain)(m)

    @driver_method
    def train(self, timeout=32):
        self.lane0.delay = 15
        print("doing word alignment...")
        for i in range(timeout):
            if self.lane0.output == 0b00010110:
                print("-> {} slips".format(i))
                print("training lane 0...")
                self.lane0.train()
                print("training lane 1...")
                self.lane1.train()
                print("training lane 2...")
                self.lane2.train()
                print("training lane 3...")
                self.lane3.train()
                self.trained = True
                return
            else:
                self.word_aligner.slip()
        raise TimeoutError()


class WordAligner(Elaboratable):
    def __init__(self, ddr_domain, lane_output):
        self.ddr_domain = ddr_domain

        self.lane_output = lane_output
        self.do_bitslip = ControlSignal()

        self.bitslip = Signal()

    def elaborate(self, platform):
        m = Module()

        m.submodules.clk_div_quater = ClkDiv(self.ddr_domain, "sync", div=4, input_frequency=400e6, bitslip=self.bitslip)

        last_do_bitslip = Signal()
        m.d.sync += last_do_bitslip.eq(self.do_bitslip)
        with m.If(last_do_bitslip != self.do_bitslip):
            m.d.comb += self.bitslip.eq(1)

        return m

    @driver_method
    def slip(self):
        self.do_bitslip = not self.do_bitslip


class LaneBitAligner(Elaboratable):
    def __init__(self, input, in_testpattern_mode, ddr_domain, bitslip_signal, testpattern=0b00010110):
        """
        Does bit alignment of one lane usig a given testpattern if in_testpattern_mode is high
        """
        self.input = input
        self.bitslip_signal = bitslip_signal
        self.in_testpattern_mode = in_testpattern_mode

        self.ddr_domain = ddr_domain
        self.testpattern = testpattern

        self.delay = ControlSignal(5, reset=15)
        self.error = StatusSignal(32)

        self.output = StatusSignal(8)

    def elaborate(self, platform):
        m = Module()

        delayed = Signal()
        m.submodules.delayd = Instance(
            "DELAYD",

            i_A=self.input,
            i_DEL0=self.delay[0],
            i_DEL1=self.delay[1],
            i_DEL2=self.delay[2],
            i_DEL3=self.delay[3],
            i_DEL4=self.delay[4],

            o_Z=delayed,
        )
        iserdes = m.submodules.iserdes = ISerdes8(delayed, self.ddr_domain, word_domain="sync", invert=True)
        m.d.comb += self.output.eq(iserdes.output)
        m.d.comb += iserdes.bitslip.eq(self.bitslip_signal)

        with m.If(self.in_testpattern_mode & (self.output != self.testpattern)):
            m.d.sync += self.error.eq(self.error + 1)

        return m

    @driver_method
    def train(self):
        from time import sleep
        start_current = 0
        start_longest = 0
        len_longest = 0
        was_good = True
        for i in range(32):
            self.delay = i
            e_start = self.error
            sleep(0.01)
            difference = self.error - e_start
            if difference == 0 and not was_good:
                start_current = i
            elif ((difference != 0) or (i == 31)) and was_good:
                len = i - start_current
                if len > len_longest:
                    len_longest = len
                    start_longest = start_current
            print(i, difference)
            was_good = difference == 0
        self.delay = int(start_longest + (len_longest / 2))
        print("-> delay tap", self.delay)
