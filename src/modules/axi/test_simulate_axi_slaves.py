from nmigen import *
from nmigen.test.utils import FHDLTestCase
from nmigen.back.pysim import Simulator, Tick, Settle, Passive

from modules.axi.axil_reg import AxiLiteReg


class TestAxiSlave(FHDLTestCase):
    def check_read_transaction(self, address, slave):
        sim = Simulator(slave)

        def timeout(expr, timeout=20):
            for i in range(timeout):
                if (yield expr):
                    break
            raise TimeoutError()

        def process():
            yield slave.axi.read_address.value.eq(address)
            yield slave.axi.read_address.valid.eq(1)
            while not (yield slave.axi.read_address.ready):
                yield
            # yield from timeout(slave.axi.read_data.valid)


        sim.add_clock(1e-6)
        sim.add_sync_process(process)
        with sim.write_vcd("test.vcd", "test.gtkw",  traces=(slave.axi._rhs_signals())):
            sim.run_until(10e-6, run_passive=True)

    def test_read_axil_reg(self):
        self.check_read_transaction(0x1231456, AxiLiteReg(width=32, base_address=0x123456, name="test"))