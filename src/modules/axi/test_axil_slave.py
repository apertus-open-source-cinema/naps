from nmigen import *
from nmigen.asserts import *

from nmigen.test.utils import FHDLTestCase

from modules.axi.axil_slave import AxiLiteReg


class AxiLiteCheck(Elaboratable):
    def __init__(self, dut):
        self.dut = dut

    def elaborate(self, platform):
        m = Module()
        m.submodules.dut = dut = self.dut

        with m.If(Initial()):
            m.d.comb += Assume(dut.reg == 0)

        m.d.comb += Assert(dut.reg == 0x00)
        return m


class TestAxiLiteSlave(FHDLTestCase):
    def test_valid_axil(self):
        axil_slave = AxiLiteReg(width=8, base_address=0x123456)
        self.assertFormal(AxiLiteCheck(axil_slave), mode="bmc", depth=10)
