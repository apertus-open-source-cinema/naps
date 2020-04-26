from nmigen import *
from nmigen.test.utils import FHDLTestCase
from nmigen.back.pysim import Simulator, Tick, Settle, Passive

from modules.axi.axi import AxiInterface
from modules.axi.axil_reg import AxiLiteReg
from modules.axi.interconnect import AxiInterconnect


class TestAxiSlave(FHDLTestCase):
    def check_read_transaction(self, addresses, dut, filename="test"):
        sim = Simulator(dut)
        axi = dut.axi

        def timeout(expr, timeout=10):
            for i in range(timeout):
                yield
                if (yield expr):
                    return
            raise TimeoutError()

        def process():
            for addr in addresses:
                yield axi.read_address.value.eq(addr)
                yield axi.read_address.valid.eq(1)
                yield from timeout(axi.read_address.ready)
                yield axi.read_address.valid.eq(0)
                yield from timeout(axi.read_data.valid)
                yield axi.read_data.ready.eq(1)



        sim.add_clock(1e-6)
        sim.add_sync_process(process)
        with sim.write_vcd("{}.vcd".format(filename), "{}.gtkw".format(filename), traces=(dut.axi._rhs_signals())):
            sim.run()

    def test_read_axil_reg(self, addr=0x123456):
        dut = AxiLiteReg(width=32, base_address=addr, name="test")
        self.check_read_transaction((addr,), dut, filename="test_read_axil_reg")

    def test_read_interconnect_axil_reg(self, addr=0x123456, num_regs=10):
        addrs = [addr + i for i in range(num_regs)]
        m = Module()

        m.axi = AxiInterface(addr_bits=32, data_bits=32, master=True, lite=True)
        interconnect = m.submodules.interconnect = AxiInterconnect(m.axi)
        for addr in addrs:
            axil_reg = AxiLiteReg(width=32, base_address=addr, name="test")
            m.d.comb += interconnect.get_port().connect_slave(axil_reg.axi)
            m.submodules += axil_reg

        self.check_read_transaction(addrs, dut=m, filename="test_read_interconnect_axil_reg")