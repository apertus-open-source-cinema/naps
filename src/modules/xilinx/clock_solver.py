"""Generates multiple Clocks using the Xilinx clocking primitives"""

from itertools import product
from nmigen import *
from util.logger import log

from .blocks import Mmcm, Pll


class ClockSolver:
    def __init__(self, clocks, in_clk, f_in):
        self.f_in = f_in
        self.in_clk = in_clk
        self.clocks = clocks.copy()
        self.available_resources = ([Mmcm()] * 2) + ([Pll()] * 2)

    def elaborate(self, platform):
        mod = Module()
        
        while self.clocks:
            resource = self.available_resources.pop(0)
            frequencies = list(self.clocks.keys())[0:resource.CLOCK_COUNT]

            (m, d), dividers = ClockSolver._solve(resource, self.f_in, frequencies)
            mod.d.comb += resource.get_in_clk().eq(self.in_clk)
            resource.set_vco(m, d)
            for d, f in zip(dividers, frequencies):
                s = self.clocks[f]
                clock = resource.get_clock(d)
                mod.d.comb += s.eq(clock)
                self.clocks.pop(f)
                setattr(mod.submodules, "{}".format(resource.__class__.__name__), resource)
        return mod

    @staticmethod
    def _solve(cr, f_in, clock_freqs, output_divider_step=1):
        assert len(clock_freqs) < cr.CLOCK_COUNT

        possible_vco_freqs = [(f_in * (m / d), (m, d)) for m, d in product(range(1, 128), range(1, 128))
                              if cr.VCO_MIN < (f_in * (m / d)) < cr.VCO_MAX]

        def dividers(f_in, f_out):
            return [round(f_in / target_freq / output_divider_step) * output_divider_step for target_freq in f_out]

        rated_vco_freqs = [(
            [(f_target - (f_vco / d)) ** 2 for f_target, d in zip(clock_freqs, dividers(f_vco, clock_freqs))],
            comb, dividers(f_vco, clock_freqs)
        ) for f_vco, comb in possible_vco_freqs]

        return max(rated_vco_freqs, key=lambda x: x[0])[1:]
