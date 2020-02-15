from functools import reduce

from nmigen import *
from nmigen.asserts import *

from nmigen.test.utils import FHDLTestCase

from modules.axi.axil_slave import AxiLiteReg


def PastAny(expr, clocks, domain=None):
    return reduce(lambda a, b: a | b, [Past(expr, x, domain) for x in range(clocks)])


class AxiLiteCheck(Elaboratable):
    def __init__(self, dut, address_range, max_latency):
        self.dut = dut
        self.address_range = address_range
        self.max_latency = max_latency

    def elaborate(self, platform):
        m = Module()
        m.submodules.dut = dut = self.dut
        axi_bus = dut.bus
        print(axi_bus)

        is_read = Signal()
        m.d.comb += is_read.eq(
            (self.address_range.start <= axi_bus.read_address.value) &
            (axi_bus.read_address.value < self.address_range.stop) &
            axi_bus.read_address.valid
        )
        was_addressed_writing = Signal()
        m.d.sync += was_addressed_writing.eq(
            (
                    (self.address_range.start <= axi_bus.write_address.value) &
                    (axi_bus.write_address.value < self.address_range.stop) &
                    axi_bus.write_address.valid
            ) | was_addressed_writing
        )

        is_written = Signal()
        m.d.comb += is_written.eq(axi_bus.write_data.valid & was_addressed_writing)

        # prove, that the peripheral does not do anything if it is not addressed
        m.d.comb += Assert(Rose(axi_bus.read_data.valid).implies(PastAny(is_read, clocks=self.max_latency)))
        m.d.comb += Assert(Rose(axi_bus.write_response.valid).implies(PastAny(is_written, clocks=self.max_latency)))

        # prove, that it answers, when it is addressed
        m.d.comb += Assert(Rose(is_read, clocks=2).implies(axi_bus.read_data.valid))

        return m


class TestAxiLiteSlave(FHDLTestCase):
    def test_valid_axil(self):
        base_address = 0x42
        axil_slave = AxiLiteReg(width=8, base_address=base_address)
        valid_address_range = range(base_address, base_address + 1)
        self.assertFormal(AxiLiteCheck(axil_slave, valid_address_range, max_latency=4), mode="bmc", depth=20)
