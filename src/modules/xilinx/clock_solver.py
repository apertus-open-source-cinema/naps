"""Generates multiple Clocks using the Xilinx clocking primitives"""

from nmigen import *

from .blocks import MMCM


class ClockSolver:
    def __init__(self, clocks):
        self.clocks = clocks

    def elaborate(self, platform):
        m = Module()

        mmcm0 = m.submodules.mmcm0 = MMCM()

        return m
