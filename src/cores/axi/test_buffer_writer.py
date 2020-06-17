import unittest

from nmigen import *

from cores.ring_buffer_address_storage import RingBufferAddressStorage
from cores.stream.stream import StreamEndpoint
from util.sim import SimPlatform
from cores.axi.axi_endpoint import AxiEndpoint, Response, AddressChannel, BurstType, DataChannel
from cores.axi.buffer_writer import AxiBufferWriter, AddressGenerator
from util.sim import wait_for, pulse, do_nothing


def answer_channel(channel, always_ready=True):
    if always_ready:
        yield channel.ready.eq(1)
    yield from wait_for(channel.valid)
    if isinstance(channel, AddressChannel):
        to_return = (
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


def answer_write_burst(axi: AxiEndpoint):
    memory = {}
    addr, burst_len, burst_type, beat_size_bytes = yield from answer_channel(axi.write_address)
    assert 2 ** beat_size_bytes == axi.data_bytes
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

    return memory, accepted


class TestSimAxiWriter(unittest.TestCase):
    def test_buffer_change(self, data_len=50):
        axi = AxiEndpoint(addr_bits=32, data_bits=64, master=False, lite=False, id_bits=12)

        ringbuffer = RingBufferAddressStorage(0x1000, 2, base_address=0)
        stream_source = StreamEndpoint(Signal(64), is_sink=False)

        dut = AxiBufferWriter(ringbuffer, stream_source, axi, fifo_depth=data_len)

        def testbench():
            gold = {}

            gold_gen = {
                "current_buffer": 0,
                "current_address": ringbuffer.buffer_base_list[0]
            }

            def change_buffer():
                gold_gen["current_buffer"] = (gold_gen["current_buffer"] + 1) % len(ringbuffer.buffer_base_list)
                gold_gen["current_address"] = ringbuffer.buffer_base_list[gold_gen["current_buffer"]]
                yield stream_source.last.eq(1)

            def put_data(data):
                gold[gold_gen["current_address"]] = data
                gold_gen["current_address"] += axi.data_bytes
                yield stream_source.valid.eq(1)
                yield stream_source.payload.eq(data)

            # first, fill in some data:
            for i in range(data_len):
                yield from put_data(i)
                # yield dut.change_buffer.eq(0)
                yield from change_buffer()
                yield
            yield stream_source.valid.eq(0)

            memory = {}
            accepted = 0
            while accepted < data_len:
                memory_fragment, accepted_frag = (yield from answer_write_burst(axi))
                memory.update(memory_fragment)
                accepted += accepted_frag
                yield

            self.assertEqual(gold, memory)
            self.assertFalse((yield dut.error))

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut, testbench)

    def test_basic(self, data_len=50):
        axi = AxiEndpoint(addr_bits=32, data_bits=64, master=False, lite=False, id_bits=12)

        ringbuffer = RingBufferAddressStorage(0x1000, 2, base_address=0)
        stream_source = StreamEndpoint(Signal(64), is_sink=False)

        dut = AxiBufferWriter(ringbuffer, stream_source, axi, fifo_depth=data_len)

        def testbench():
            # first, fill in some data:
            for i in range(data_len):
                yield stream_source.payload.eq(i)
                yield stream_source.valid.eq(1)
                yield
            yield stream_source.valid.eq(0)

            memory = {}
            while len(memory) < 50:
                memory.update((yield from answer_write_burst(axi))[0])

            self.assertEqual({ringbuffer.buffer_base_list[0] + i * axi.data_bytes: i for i in range(50)}, memory)
            self.assertFalse((yield dut.error))

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut, testbench)

    def test_memory(self):
        m = Module()
        memory = Memory(width=8, depth=8)
        read_port = m.submodules.read_port = memory.read_port(transparent=False)
        write_port = m.submodules.write_port = memory.write_port()
        lol = Signal()
        m.d.sync += lol.eq(Cat(read_port.en, read_port.data, read_port.addr, write_port.en, write_port.data, write_port.addr))

        def testbench():
            for i in range(8):
                yield write_port.addr.eq(i)
                yield write_port.data.eq(i)
                yield write_port.en.eq(1)
                yield
            yield write_port.en.eq(0)
            for i in range(8):
                yield read_port.addr.eq(i)
                yield read_port.en.eq(1)
                yield
            yield read_port.en.eq(0)

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.sim(m, testbench)


class TestAddressGenerator(unittest.TestCase):
    def test_basic(self, inc=5):
        ringbuffer = RingBufferAddressStorage(0x1000, 2, base_address=0)
        dut = AddressGenerator(ringbuffer, addr_bits=32, max_incr=inc)

        def testbench():
            yield dut.inc.eq(inc)
            for i in range(10):
                yield from pulse(dut.request)
                yield from wait_for(dut.valid, must_clock=False)
                self.assertEqual(ringbuffer.buffer_base_list[0] + i * inc, (yield dut.addr))
                yield from pulse(dut.done)
            yield from pulse(dut.change_buffer)
            yield from do_nothing()
            for i in range(10):
                yield from pulse(dut.request)
                yield from wait_for(dut.valid)
                self.assertEqual(ringbuffer.buffer_base_list[1] + i * inc, (yield dut.addr))
                yield from pulse(dut.done)

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut, testbench, [dut.request, dut.change_buffer, dut.addr, dut.valid, dut.done])
