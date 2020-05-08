from nmigen import *
from nmigen.test.utils import FHDLTestCase

from modules.axi.axi import AxiInterface, Response, AddressChannel, BurstType, DataChannel
from modules.axi.buffer_writer import AxiBufferWriter, AddressGenerator
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
    elif isinstance(channel, DataChannel):
        to_return = ((yield channel.value), (yield channel.last), (yield channel.byte_strobe))
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
    accepted = 0
    for i in range(burst_len):
        value, last, byte_strobe = yield from answer_channel(axi.write_data)
        if i == burst_len - 1:
            assert last
        if byte_strobe != 0:
            memory[addr + i * axi.data_bytes] = value
            accepted += 1
    respond_channel(axi.write_response)

    return (memory, accepted)


class TestSimAxiWriter(FHDLTestCase):
    def test_buffer_change(self, buffer_base_list=(1000, 2000), burst_len=16, data_len=50):
        axi = AxiInterface(addr_bits=32, data_bits=64, master=False, lite=False, id_bits=12)
        dut = AxiBufferWriter(axi, buffer_base_list, max_burst_length=burst_len, max_buffer_size=0x1000, fifo_depth=data_len)

        def testbench():
            gold = {}

            gold_gen = {
                "current_buffer": 0,
                "current_address": buffer_base_list[0]
            }

            def change_buffer():
                gold_gen["current_buffer"] = (gold_gen["current_buffer"] + 1) % len(buffer_base_list)
                gold_gen["current_address"] = buffer_base_list[gold_gen["current_buffer"]]
                yield dut.change_buffer.eq(1)

            def put_data(data):
                gold[gold_gen["current_address"]] = data
                gold_gen["current_address"] += axi.data_bytes
                yield dut.data_valid.eq(1)
                yield dut.data.eq(data)

            # first, fill in some data:
            for i in range(data_len):
                yield from put_data(i)
                #yield dut.change_buffer.eq(0)
                yield from change_buffer()
                yield
            yield dut.data_valid.eq(0)

            memory = {}
            accepted = 0
            while accepted < data_len:
                memory_fragment, accepted_frag = (yield from answer_write_burst(axi))
                memory.update(memory_fragment)
                accepted += accepted_frag
                yield

            self.assertEqual(gold, memory)
            self.assertFalse((yield dut.error))

        sim(dut, testbench, "axi_writer_buffer_change", [*dut.axi._rhs_signals(), dut.address_generator.request, dut.address_generator.valid, dut.address_generator.valid])

    def test_basic(self, buffer_base_list=(1000, 2000), burst_len=16):
        axi = AxiInterface(addr_bits=32, data_bits=64, master=False, lite=False, id_bits=12)
        dut = AxiBufferWriter(axi, buffer_base_list, max_burst_length=burst_len, max_buffer_size=0x1000, fifo_depth=50)

        def testbench():
            # first, fill in some data:
            for i in range(50):
                yield dut.data.eq(i)
                yield dut.data_valid.eq(1)
                yield

            yield dut.data_valid.eq(0)
            memory = {}
            while len(memory) < 50:
                memory.update((yield from answer_write_burst(axi))[0])

            self.assertEqual({buffer_base_list[0] + i * axi.data_bytes: i for i in range(50)}, memory)
            self.assertFalse((yield dut.error))

        sim(dut, testbench, "axi_writer_basic",
            [*dut.axi._rhs_signals(), dut.address_generator.request, dut.address_generator.valid,
             dut.address_generator.valid])


class TestAddressGenerator(FHDLTestCase):
    def test_basic(self, inc=5):
        buffer_base_list = [1000, 2000]
        dut = AddressGenerator(buffer_base_list, max_buffer_size=0x1000, addr_bits=32, max_incr=inc)

        def testbench():
            yield dut.inc.eq(inc)
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
