from functools import reduce

from nmigen import *
from nmigen.asserts import *

from nmigen.test.utils import FHDLTestCase

from modules.axi.axil_i2c import AxiLiteI2c
from modules.axi.axil_reg import AxiLiteReg
from modules.vendor.glasgow_i2c.i2c import _DummyPads


def nAny(iterator):
    return reduce(lambda a, b: a | b, iterator)


def PastAny(expr, clocks, domain=None):
    return nAny([Past(expr, x, domain) for x in range(clocks)])


class AxiLiteCheck(Elaboratable):
    def __init__(self, dut, address_range, max_latency):
        self.dut = dut
        self.address_range = address_range
        self.max_latency = max_latency

    def elaborate(self, platform):
        m = Module()
        m.submodules.dut = dut = self.dut
        axi_bus = dut.axi

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
        m.d.comb += Assert(
            nAny(Rose(is_read, clocks=x).implies(axi_bus.read_data.valid) for x in range(self.max_latency)))
        m.d.comb += Assert(
            nAny(Rose(is_written, clocks=x).implies(axi_bus.write_response.valid) for x in range(self.max_latency)))
        m.d.comb += Assert(~Rose(is_read, clocks=15))
        # TODO: prove that the outputs dont change after they settled

        # TODO: prove, that everything goes to the initial state after reset (is this nescessary for nmigen designs?)
        return m


class TestAxiLiteSlave(FHDLTestCase):
    def test_axil_reg(self):
        base_address = 0x42
        axil_slave = AxiLiteReg(width=8, base_address=base_address)
        valid_address_range = range(base_address, base_address + 1)
        self.assertFormal(AxiLiteCheck(axil_slave, valid_address_range, max_latency=4), mode="bmc", depth=20)

    def test_axil_i2c(self):
        # TODO: How can this pass? it odesnt answer!
        base_address = 0x42
        addr_bytes = 2
        pads = _DummyPads()
        axil_slave = AxiLiteI2c(pads, clock_divider=1, base_address=base_address, address_bytes=addr_bytes)
        valid_address_range = range(base_address, base_address+2**(8*addr_bytes))
        print(valid_address_range)

        self.assertFormal(AxiLiteCheck(axil_slave, valid_address_range, max_latency=4), mode="bmc", depth=20)
