from abc import ABC

from .xilinx_blackbox import XilinxBlackbox


class Ps7(XilinxBlackbox):
    module = "PS7"


class ClockingResource(XilinxBlackbox):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert hasattr(self.__class__, "VCO_MIN")
        assert hasattr(self.__class__, "VCO_MAX")
        assert hasattr(self.__class__, "CLOCK_COUNT")

        self.next_clk = 0

    def set_vco(self, multiplier, divider):
        self.parameters[self.__class__.VCO_MULT_NAME] = multiplier
        self.parameters[self.__class__.VCO_DIV_NAME] = divider

    def get_clock(self, divider):
        assert self.next_clk < self.__class__.CLOCK_COUNT
        self.parameters[self.__class__.OUT_DIV_NAME.format(self.next_clk)] = divider
        self.next_clk += 1
        return self[self.__class__.OUT_DIV_PORT.format(self.next_clk - 1)]


class Mmcm(ClockingResource):
    module = "MMCME2_BASE"
    VCO_MIN = 600e6
    VCO_MAX = 1200e6
    CLOCK_COUNT = 7
    OUTPUT_DIV_STEP = 0.25

    VCO_MULT_NAME = "CLKFBOUT_MULT_F"
    VCO_DIV_NAME = "DIVCLK_DIVIDE"
    OUT_DIV_NAME = "CLKOUT{}_DIVIDE"
    OUT_DIV_PORT = "CLKOUT{}"


class Pll(ClockingResource):
    module = "PLLE2_BASE"
    VCO_MIN = 800e6
    VCO_MAX = 1600e6
    OUTPUT_DIV_STEP = 1

    CLOCK_COUNT = 6
    VCO_MULT_NAME = "CLKFBOUT_MULT_F"
    VCO_DIV_NAME = "DIVCLK_DIVIDE"
    OUT_DIV_NAME = "CLKOUT{}_DIVIDE"
    OUT_DIV_PORT = "CLKOUT{}"
