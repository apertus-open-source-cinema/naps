from nmigen import *
from nmigen.test.utils import FHDLTestCase

from modules.axi.axi import Response
from soc.peripherals.register import SocRegister
from soc.peripherals.csr_auto import AutoCsrBank
from test.ZyncSocTestPlatform import ZynqSocTestPlatform
from util.sim import wait_for


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
    return result, response


def axil_read(axi, addr):
    yield from write_to_channel(axi.read_address, addr)
    value, response = (yield from read_from_channel(axi.read_data))
    assert Response.OKAY.value == response
    return value


def axil_write(axi, addr, data):
    yield from write_to_channel(axi.write_address, addr)
    yield from write_to_channel(axi.write_data, data)
    result, response = (yield from read_from_channel(axi.write_response))
    assert Response.OKAY.value == response


class TestAxiSlave(FHDLTestCase):
    def test_reg(self, addr=123456, testdata=123456):
        platform = ZynqSocTestPlatform(addr)
        dut = SocRegister(width=32, name="test")

        def testbench():
            axi = platform.axi_lite_master

            yield from axil_read(axi, addr)
            yield from axil_write(axi, addr, testdata)
            self.assertEqual(testdata, (yield from axil_read(axi, addr)))

        platform.sim(dut, testbench)

    def test_auto_csr_bank(self, base_addr=123456, num_csr=10, testdata=0x12345678):
        platform = ZynqSocTestPlatform(base_addr)
        csr_bank = AutoCsrBank()
        for i in range(num_csr):
            csr_bank.reg("csr#{}".format(i), width=32, writable=True)

        print(csr_bank._memory_map)

        def testbench():
            axi = platform.axi_lite_master
            for addr in [base_addr + (i * 4) for i in range(num_csr)]:
                yield from axil_read(axi, addr)
                yield from axil_write(axi, addr, testdata)
                self.assertEqual(testdata, (yield from axil_read(axi, addr)))

        platform.sim(csr_bank, testbench)
