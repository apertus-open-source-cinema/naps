from nmigen import *

from nmigen.build import Clock
from numpy import arange
from modules.xilinx import blocks
from modules.xilinx.blocks import Bufg


class Mmcm(blocks.Mmcm):
    vco_multipliers = list(arange(2, 64, 0.125))
    vco_dividers = range(1, 106)
    output_0_dividers = list(arange(1, 128, 0.125))
    output_dividers = range(1, 128)

    @staticmethod
    def is_valid_vco_conf(input_freq, mul, div, exception=False):
        if not mul in Mmcm.vco_multipliers:
            if exception: raise ValueError
            return False
        if not div in Mmcm.vco_dividers:
            if exception: raise ValueError
            return False
        vco_freq = input_freq * mul / div
        if 600e6 > vco_freq:
            if exception: raise ValueError
            return False
        if 1200e6 < vco_freq:
            if exception: raise ValueError
            return False
        return True

    def __init__(self, input_clock, vco_mul, vco_div, input_domain="sync"):
        Mmcm.is_valid_vco_conf(input_clock, vco_mul, vco_div, exception=True)
        super().__init__(
            bandwidth="OPTIMIZED", ref_jitter1=0.01,
            clkfbout_mult_f=vco_mul, clkfbout_phase=0.0, divclk_divide=vco_div,
        )
        m = self.m = Module()
        m.d.comb += self.clk.fbin.eq(self.clk.fbout)
        m.d.comb += self.clk.in_[1].eq(ClockSignal(input_domain))

        self._input_clock = input_clock
        self._vco = Clock(input_clock * vco_mul / vco_div)
        self._clock_constraints = {}

    def output_domain(self, domain_name, divisor, number=None, bufg=True):
        if number is None:
            number = next(x for x in range(7) if x not in self._clock_constraints.keys())
        assert number not in self._clock_constraints.keys(), "port {} is already taken".format(number)

        assert divisor in (Mmcm.output_dividers if number != 0 else Mmcm.output_0_dividers)

        divide_param = "CLKOUT{}_DIVIDE{}".format(number, "_f" if number == 0 else "")
        self.parameters[divide_param] = divisor
        self.parameters["CLKOUT{}_PHASE".format(number)] = 0.0

        m = self.m

        clock_signal = Signal(name="mmcm_out_{}".format(number), attrs={"KEEP": "TRUE"})
        m.d.comb += clock_signal.eq(self.clk.out[number])

        if bufg:
            bufg = m.submodules["bufg_{}".format(number)] = Bufg()
            m.d.comb += bufg.i.eq(clock_signal)
            output = bufg.o
        else:
            output = clock_signal

        m.domains += ClockDomain(domain_name)
        m.d.comb += ClockSignal(domain_name).eq(output)

        frequency = self._vco.frequency / divisor
        self._clock_constraints[number] = (clock_signal, frequency)
        return Clock(frequency)

    def elaborate(self, platform):
        m = Module()

        m.submodules.mmcm_block = super().elaborate(platform)
        m.submodules.connections = self.m

        for i, (clock_signal, frequency) in self._clock_constraints.items():
            platform.add_clock_constraint(clock_signal, frequency)

        return m
