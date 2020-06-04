import unittest

from nmigen import *

from soc.axi.axi_interface import Response, AxiInterface
from util.sim import SimPlatform
from soc.peripherals.csr_bank import CsrBank
from soc.zynq.zynq_soc_platform import ZynqSocPlatform
from util.sim import wait_for, do_nothing


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


class TestAxiSlave(unittest.TestCase):
    def test_csr_bank(self, num_csr=10, testdata=0x12345678):
        platform = ZynqSocPlatform(SimPlatform())
        csr_bank = CsrBank()
        for i in range(num_csr):
            csr_bank.reg("csr#{}".format(i), Signal(32),  writable=True)

        def testbench():
            axi = platform.axi_lite_master
            for addr in [0x4000_0000 + (i * 4) for i in range(num_csr)]:
                yield from axil_read(axi, addr)
                yield from axil_write(axi, addr, testdata)
                self.assertEqual(testdata, (yield from axil_read(axi, addr)))

        platform.sim(csr_bank, (testbench, "axi_csr"))

    def test_simple_test_csr_bank(self):
        platform = ZynqSocPlatform(SimPlatform())
        csr_bank = CsrBank()
        csr_bank.reg("csr", Signal(32), writable=True)

        def testbench():
            axi: AxiInterface = platform.axi_lite_master
            yield axi.read_address.value.eq(0x4000_0000)
            yield axi.read_address.valid.eq(1)
            yield from do_nothing()


        platform.sim(csr_bank, (testbench, "axi_csr"))
