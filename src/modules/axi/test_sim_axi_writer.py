from nmigen import *
from nmigen.test.utils import FHDLTestCase

from modules.axi.axi import AxiInterface, Response, AddressChannel, BurstType
from modules.axi.axi_writer import AxiHpWriter, AddressGenerator
from util.sim import sim, wait_for, pulse, do_nothing


def answer_channel(channel, always_ready=True):
    if always_ready:
        yield channel.ready.eq(1)
    yield from wait_for(channel.valid)
    if isinstance(channel, AddressChannel):
        to_return =(
            (yield channel.value),
            (yield channel.burst_len) + 1,
            (yield channel.burst_type),
            (yield channel.beat_size_bytes)
        )
    else:
        to_return = ((yield channel.value), (yield channel.last))
    if not always_ready:
        yield from pulse(channel.ready)
    else:
        yield channel.ready.eq(0)
    return to_return


def respond_channel(channel, resp=Response.OKAY):
    yield channel.resp.eq(resp)
    pulse(channel.valid)


def answer_write_burst(axi: AxiInterface):
    memory = {}
    addr, burst_len, burst_type, beat_size_bytes = yield from answer_channel(axi.write_address)
    assert 2**beat_size_bytes == axi.data_bytes
    assert burst_type == BurstType.INCR.value
    for i in range(burst_len):
        value, last = yield from answer_channel(axi.write_data)
        if i == burst_len - 1:
            assert last
        memory[addr + i * axi.data_bytes] = value
    respond_channel(axi.write_response)

    return memory


class TestSimAxiWriter(FHDLTestCase):
    def test_basic(self, buffer_base_list=(1000, 2000), burst_len=16):
        axi = AxiInterface(addr_bits=32, data_bits=64, master=False, lite=False, id_bits=12)
        dut = AxiHpWriter(axi, buffer_base_list, burst_length=burst_len)

        def testbench():
            # first, fill in some data:
            for i in range(50):
                yield dut.data.eq(i)
                yield dut.data_valid.eq(1)
                yield
            yield dut.data_valid.eq(0)
            memory = {}
            memory.update((yield from answer_write_burst(axi)))
            yield from do_nothing()
            memory.update((yield from answer_write_burst(axi)))
            self.assertEqual({buffer_base_list[0] + i * axi.data_bytes: i for i in range(burst_len*2)}, memory)
            self.assertFalse((yield dut.error))

        sim(dut, testbench, "axi_writer_basic", [*dut.axi._rhs_signals(), dut.address_generator.request, dut.address_generator.valid, dut.address_generator.valid, dut.address_generator.lol])


class TestAddressGenerator(FHDLTestCase):
    def test_basic(self, inc=1):
        buffer_base_list = [1000, 2000]
        dut = AddressGenerator(buffer_base_list, max_buffer_size=0x1000, addr_bits=32, inc=inc)

        def testbench():
            for i in range(10):
                yield from pulse(dut.request)
                yield from wait_for(dut.valid, must_clock=False)
                self.assertEqual(buffer_base_list[0] + i * inc, (yield dut.addr))
                yield from pulse(dut.done)
            yield from pulse(dut.change_buffer)
            yield from do_nothing()
            for i in range(10):
                yield from pulse(dut.request)
                yield from wait_for(dut.valid)
                self.assertEqual(buffer_base_list[1] + i * inc, (yield dut.addr))
                yield from pulse(dut.done)

        sim(dut, testbench, "addr_generator", [dut.request, dut.change_buffer, dut.addr, dut.valid, dut.done])
