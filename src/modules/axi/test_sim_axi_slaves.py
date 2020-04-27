from nmigen import *
from nmigen.test.utils import FHDLTestCase
from nmigen.back.pysim import Simulator, Tick, Settle, Passive

from modules.axi.axi import AxiInterface, Response
from modules.axi.axil_csr import AxilCsrBank
from modules.axi.axil_reg import AxiLiteReg
from modules.axi.interconnect import AxiInterconnect


def wait_for(expr, timeout=100):
    for i in range(timeout):
        yield
        if (yield expr):
            return
    raise TimeoutError("{} did not become '1' within {} cycles".format(expr, timeout))


def write_to_channel(channel, value):
    yield channel.value.eq(value)
    yield channel.valid.eq(1)
    yield from wait_for(channel.ready)
    yield channel.valid.eq(0)


def read_from_channel(channel):
    yield from wait_for(channel.valid)
    yield channel.ready.eq(1)
    if hasattr(channel, "value"):
        result = (yield channel.value)
    else:
        result = None
    response = (yield channel.resp)
    yield
    yield channel.ready.eq(0)
    return (result, response)


def axil_read(axi, addr):
    yield from write_to_channel(axi.read_address, addr)
    return (yield from read_from_channel(axi.read_data))


def axil_write(axi, addr, data):
    yield from write_to_channel(axi.write_address, addr)
    yield from write_to_channel(axi.write_data, data)
    return (yield from read_from_channel(axi.write_response))


def sim(dut, testbench, filename, traces):
    sim = Simulator(dut)

    sim.add_clock(1e-6)
    sim.add_sync_process(testbench)
    with sim.write_vcd(".sim_{}.vcd".format(filename), ".sim_{}.gtkw".format(filename), traces=traces):
        sim.run()


class TestAxiSlave(FHDLTestCase):
    def test_axil_reg(self, addr=0x123456, testdata=0x12345678):
        dut = AxiLiteReg(width=32, base_address=addr, name="test")

        def testbench():
            yield from axil_read(dut.axi, addr)
            yield from axil_write(dut.axi, addr, testdata)
            self.assertEqual((yield from axil_read(dut.axi, addr)), (testdata, Response.OKAY.value))

        sim(dut, testbench, filename="axil_reg", traces=dut.axi._rhs_signals())

    def test_interconnect_axil_reg(self, base_addr=0x123456, num_regs=10, testdata=0x12345678):
        addrs = [base_addr + i for i in range(num_regs)]
        m = Module()

        axi = AxiInterface(addr_bits=32, data_bits=32, master=True, lite=True)
        interconnect = m.submodules.interconnect = AxiInterconnect(axi)
        for addr in addrs:
            axil_reg = AxiLiteReg(width=32, base_address=addr, name="test")
            m.d.comb += interconnect.get_port().connect_slave(axil_reg.axi)
            m.submodules += axil_reg

        def testbench():
            for addr in addrs:
                yield from axil_read(axi, addr)
                yield from axil_write(axi, addr, testdata)
                self.assertEqual((yield from axil_read(axi, addr)), (testdata, Response.OKAY.value))

        sim(m, testbench, filename="interconnect_axil_reg", traces=axi._rhs_signals())

    def test_csr_bank(self, base_addr=0x123456, num_csr=10, testdata=0x12345678):
        m = Module()

        axi = AxiInterface(addr_bits=32, data_bits=32, master=True, lite=True)
        csr_bank = m.submodules.csr_bank = AxilCsrBank(axi, base_addr)
        for i in range(num_csr):
            csr_bank.reg("csr#{}".format(i), width=i, writable=True)

        def testbench():
            for addr in [base_addr + (i * 4) for i in range(num_csr)]:
                yield from axil_read(axi, addr)
                yield from axil_write(axi, addr, testdata)
                self.assertEqual((yield from axil_read(axi, addr)), (testdata, Response.OKAY.value))

        sim(m, testbench, filename="csr_bank", traces=axi._rhs_signals())
