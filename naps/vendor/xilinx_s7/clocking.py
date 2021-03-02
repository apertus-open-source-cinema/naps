from nmigen import *
from nmigen.build import Clock
from naps import SocPlatform, StatusSignal
from naps.cores import DrpBridge, DrpInterface
from naps.util import decimal_range
from ..instance_helper import InstanceHelper

__all__ = ["ClockDivider", "BufIO", "BufG", "Pll", "Mmcm"]


class ClockDivider(Elaboratable):
    def __init__(self, i, divider):
        self.divider = divider
        self.i = i
        self.o = Signal()

    def elaborate(self, platform):
        return Instance(
            "BUFR",
            p_BUFR_DIVIDE=self.divider,
            p_SIM_DEVICE="7SERIES",
            i_CE=1,
            i_CLR=ResetSignal(),
            i_I=self.i,
            o_O=self.o
        )


class BufIO(Elaboratable):
    def __init__(self, i):
        self.i = i
        self.o = Signal()

    def elaborate(self, platform):
        return Instance("BUFIO", i_I=self.i, o_O=self.o)


class BufG(Elaboratable):
    def __init__(self, i):
        self.i = i
        self.o = Signal()

    def elaborate(self, platform):
        return Instance("BUFG", i_I=self.i, o_O=self.o)


_Pll = InstanceHelper("+/xilinx/cells_xtra.v", "PLLE2_ADV")


class Pll(Elaboratable):
    vco_multipliers = list(range(2, 64))
    vco_dividers = list(range(1, 56))
    output_dividers = list(range(1, 128))

    @staticmethod
    def is_valid_vco_conf(input_freq, mul, div, exception=False):
        if not mul in Pll.vco_multipliers:
            if exception:
                raise ValueError(f'mul {mul} is not an allowed multiplier')
            return False
        if not div in Pll.vco_dividers:
            if exception:
                raise ValueError(f'div {div} is not an allowed divider')
            return False
        vco_freq = input_freq * mul / div
        if 800e6 > vco_freq:
            if exception:
                raise ValueError(f'{vco_freq} is a to low vco freq. minimum is 800Mhz')
            return False
        if 1600e6 < vco_freq:
            if exception:
                raise ValueError(f'{vco_freq} is a to high vco freq. maximum is 1600Mhz')
            return False
        return True

    def __init__(self, input_freq, vco_mul, vco_div, input_domain="sync"):
        Pll.is_valid_vco_conf(input_freq, vco_mul, vco_div, exception=True)
        self._pll = _Pll(
            clkin1_period=1 / input_freq * 1e9,
            clkfbout_mult=vco_mul, divclk_divide=vco_div,
        )
        m = self.m = Module()
        m.d.comb += self._pll.clk.fbin.eq(self._pll.clk.fbout)
        m.d.comb += self._pll.clk.in_[1].eq(ClockSignal(input_domain))
        m.d.comb += self._pll.clk.insel.eq(1)  # HIGH for clkin1

        self.locked = StatusSignal()

        self._input_domain = input_domain
        self._input_freq = input_freq
        self._vco = Clock(input_freq * vco_mul / vco_div)
        self._clock_constraints = {}

    def output_domain(self, domain_name, divisor, number=None, bufg=True):
        if number is None:
            number = next(x for x in range(6) if x not in self._clock_constraints.keys())
        assert number not in self._clock_constraints.keys(), "port {} is already taken".format(number)

        assert divisor in Mmcm.output_dividers

        self._pll.parameters["CLKOUT{}_DIVIDE".format(number)] = divisor
        self._pll.parameters["CLKOUT{}_PHASE".format(number)] = 0.0

        m = self.m

        clock_signal = Signal(name="pll_out_{}".format(number), attrs={"KEEP": "TRUE"})
        m.d.comb += clock_signal.eq(self._pll.clk.out[number])

        if bufg:
            # TODO: seems to not change anything
            bufg = m.submodules["bufg_{}".format(number)] = BufG(clock_signal)
            output = bufg.o
        else:
            output = clock_signal

        m.domains += ClockDomain(domain_name)
        m.d.comb += ClockSignal(domain_name).eq(output)
        m.d.comb += ResetSignal(domain_name).eq(~self.locked)

        frequency = self._vco.frequency / divisor
        self._clock_constraints[number] = (clock_signal, frequency)
        print("PLL: creating domain '{}' with frequency {}Mhz".format(domain_name, frequency / 1e6))
        return Clock(frequency)

    def elaborate(self, platform):
        m = Module()

        m.submodules.pll_block = self._pll
        m.submodules.connections = self.m

        for i, (clock_signal, frequency) in self._clock_constraints.items():
            platform.add_clock_constraint(clock_signal, frequency)

        m.d.comb += self.locked.eq(self._pll.locked)
        m.d.comb += self._pll.rst.eq(ResetSignal(self._input_domain))

        if isinstance(platform, SocPlatform):
            m.submodules.drp_bridge = DrpBridge(DrpInterface(
                self._pll.dwe, self._pll.den, self._pll.daddr, self._pll.di, self._pll.do, self._pll.drdy, self._pll.dclk
            ))

        return m


class Mmcm(Elaboratable):
    vco_multipliers = list(decimal_range(2, 64, 0.125))
    vco_dividers = list(range(1, 106))
    output_0_dividers = list(decimal_range(1, 128, 0.125))
    output_dividers = list(range(1, 128))

    @staticmethod
    def is_valid_vco_conf(input_freq, mul, div, exception=False):
        if not mul in Mmcm.vco_multipliers:
            if exception:
                raise ValueError
            return False
        if not div in Mmcm.vco_dividers:
            if exception:
                raise ValueError
            return False
        vco_freq = input_freq * mul / div
        if 600e6 > vco_freq:
            if exception:
                raise ValueError
            return False
        if 1200e6 < vco_freq:
            if exception:
                raise ValueError
            return False
        return True

    def __init__(self, input_clock, vco_mul, vco_div, input_domain="sync"):
        Mmcm.is_valid_vco_conf(input_clock, vco_mul, vco_div, exception=True)
        self._mmcm = InstanceHelper("+/xilinx/cells_xtra.v", "MMCME2_ADV")(
            clkin1_period=1 / input_clock * 1e9,
            clkfbout_mult_f=vco_mul, divclk_divide=vco_div,
        )
        m = self.m = Module()
        m.d.comb += self._mmcm.clk.fbin.eq(self._mmcm.clk.fbout)
        m.d.comb += self._mmcm.clk.in_[1].eq(ClockSignal(input_domain))
        m.d.comb += self._mmcm.clk.ins.el.eq(1)  # HIGH for clkin1

        self.locked = StatusSignal()

        self._input_domain = input_domain
        self._input_clock = input_clock
        self._vco = Clock(input_clock * vco_mul / vco_div)
        self._clock_constraints = {}

    def output_domain(self, domain_name, divisor, number=None, bufg=True):
        if number is None:
            number = next(x for x in range(7) if x not in self._clock_constraints.keys())
        assert number not in self._clock_constraints.keys(), "port {} is already taken".format(number)

        assert divisor in (Mmcm.output_dividers if number != 0 else Mmcm.output_0_dividers)

        divide_param = "CLKOUT{}_DIVIDE{}".format(number, "_f" if number == 0 else "")
        self._mmcm.parameters[divide_param] = divisor
        self._mmcm.parameters["CLKOUT{}_PHASE".format(number)] = 0.0

        m = self.m

        clock_signal = Signal(name="mmcm_out_{}".format(number), attrs={"KEEP": "TRUE"})
        m.d.comb += clock_signal.eq(self._mmcm.clk.out[number])

        if bufg:
            # TODO: seems to not change anything
            bufg = m.submodules["bufg_{}".format(number)] = BufG(clock_signal)
            output = bufg.o
        else:
            output = clock_signal

        m.domains += ClockDomain(domain_name)
        m.d.comb += ClockSignal(domain_name).eq(output)
        m.d.comb += ResetSignal(domain_name).eq(~self.locked)

        frequency = self._vco.frequency / divisor
        self._clock_constraints[number] = (clock_signal, frequency)
        print("MMCM: creating domain '{}' with frequency {}Mhz".format(domain_name, frequency / 1e6))
        return Clock(frequency)

    def elaborate(self, platform):
        m = Module()

        m.submodules.mmcm_block = self._mmcm
        m.submodules.connections = self.m

        for i, (clock_signal, frequency) in self._clock_constraints.items():
            platform.add_clock_constraint(clock_signal, frequency)

        m.d.comb += self.locked.eq(self._mmcm.locked)
        m.d.comb += self._mmcm.rst.eq(ResetSignal(self._input_domain))

        if isinstance(platform, SocPlatform):
            m.submodules.drp_bridge = DrpBridge(DrpInterface(
                self._mmcm.dwe, self._mmcm.den, self._mmcm.daddr, self._mmcm.di, self._mmcm.do, self._mmcm.drdy,
                self._mmcm.dclk
            ))

        return m
