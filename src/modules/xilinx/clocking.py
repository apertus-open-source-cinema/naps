from modules.clocking.clocking_ressource import ClockingResource
from modules.clocking.term_builder import Var
from modules.xilinx.xilinx_blackbox import XilinxBlackbox


class XilinxClockingResource(XilinxBlackbox, ClockingResource):

    def __init__(self, in_clk_freq, **kwargs):
        super().__init__(**kwargs)
        assert hasattr(self.__class__, "VCO_MIN")
        assert hasattr(self.__class__, "VCO_MAX")
        assert hasattr(self.__class__, "CLOCK_COUNT")

        self.in_clk_freq = in_clk_freq
        self.vco_mul = Var(range(1, 128))
        self.vco_div = Var(range(1, 128))
        self.output_div = [
            Var(range(1, 128, self.__class__.OUTPUT_DIV_STEP), name="output_div_{}".format(x))
            for x in range(self.__class__.CLOCK_COUNT)
        ]

    def topology(self):
        return [self.in_clk_freq * self.vco_mul / self.vco_div / o_div for o_div in self.output_div]

    def validity_constraints(self):
        return [
            (self.in_clk_freq * self.vco_mul / self.vco_div) < self.__class__.VCO_MAX,
            (self.in_clk_freq * self.vco_mul / self.vco_div) > self.__class__.VCO_MIN,
            # TODO: add (all) constraints
        ]

    def get_in_clk(self):
        return self[self.__class__.IN_CLK]

    def set_vco(self, multiplier, divider):
        self.parameters[self.__class__.VCO_MULT_NAME] = multiplier
        self.parameters[self.__class__.VCO_DIV_NAME] = divider

    def get_clock(self, divider):
        assert self.next_clk < self.__class__.CLOCK_COUNT
        self.parameters[self.__class__.OUT_DIV_NAME.format(self.next_clk)] = divider
        self.next_clk += 1
        return self[self.__class__.OUT_DIV_PORT.format(self.next_clk - 1)]


class Mmcm(XilinxClockingResource):
    module = "MMCME2_BASE"
    VCO_MIN = 600e6
    VCO_MAX = 1200e6
    CLOCK_COUNT = 7
    OUTPUT_DIV_STEP = 0.25

    IN_CLK = "CLKIN1"
    VCO_MULT_NAME = "CLKFBOUT_MULT_F"
    VCO_DIV_NAME = "DIVCLK_DIVIDE"
    OUT_DIV_NAME = "CLKOUT{}_DIVIDE_F"
    OUT_DIV_PORT = "CLKOUT{}"


class Pll(XilinxClockingResource):
    module = "PLLE2_BASE"
    VCO_MIN = 800e6
    VCO_MAX = 1600e6
    CLOCK_COUNT = 6
    OUTPUT_DIV_STEP = 1

    IN_CLK = "CLKIN1"
    VCO_MULT_NAME = "CLKFBOUT_MULT"
    VCO_DIV_NAME = "DIVCLK_DIVIDE"
    OUT_DIV_NAME = "CLKOUT{}_DIVIDE"
    OUT_DIV_PORT = "CLKOUT{}"
