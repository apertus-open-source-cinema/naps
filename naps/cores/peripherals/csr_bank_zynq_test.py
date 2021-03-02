import unittest
from naps import AxiEndpoint, axil_read, axil_write, CsrBank, ControlSignal, ZynqSocPlatform, SimPlatform, do_nothing


class TestAxiSlave(unittest.TestCase):
    def check_csr_bank(self, num_csr=10, testdata=0x12345678, use_axi_interconnect=False):
        platform = ZynqSocPlatform(SimPlatform(), use_axi_interconnect)
        csr_bank = CsrBank()
        for i in range(num_csr):
            csr_bank.reg("csr#{}".format(i), ControlSignal(32))

        def testbench():
            axi = platform.axi_lite_master
            for addr in [0x4000_0000 + (i * 4) for i in range(num_csr)]:
                yield from axil_read(axi, addr)
                yield from axil_write(axi, addr, testdata)
                self.assertEqual(testdata, (yield from axil_read(axi, addr)))

        platform.sim(csr_bank, (testbench, "axi_lite"))

    def test_csr_bank_aggregator(self):
        self.check_csr_bank(use_axi_interconnect=False)

    def test_csr_bank_interconnect(self):
        self.check_csr_bank(use_axi_interconnect=True)

    def test_simple_test_csr_bank(self):
        platform = ZynqSocPlatform(SimPlatform())
        csr_bank = CsrBank()
        csr_bank.reg("csr", ControlSignal(32))

        def testbench():
            axi: AxiEndpoint = platform.axi_lite_master
            yield axi.read_address.payload.eq(0x4000_0000)
            yield axi.read_address.valid.eq(1)
            yield from do_nothing()

        platform.sim(csr_bank, (testbench, "axi_lite"))
