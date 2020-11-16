import unittest

from nmigen import *

from lib.bus.axi.axi_endpoint import AxiEndpoint, Response, BurstType
from lib.bus.axi.buffer_writer import AxiBufferWriter
from lib.bus.ring_buffer import RingBufferAddressStorage
from lib.bus.stream.sim_util import write_to_stream, read_from_stream
from lib.bus.stream.stream import PacketizedStream
from util.sim import SimPlatform, do_nothing


def answer_write_burst(axi: AxiEndpoint):
    memory = {}
    addr, burst_len, burst_type, beat_size_bytes = yield from read_from_stream(axi.write_address, ("payload", "burst_len", "burst_type", "beat_size_bytes"))
    assert 2 ** beat_size_bytes == axi.data_bytes
    assert burst_type == BurstType.INCR.value
    accepted = 0
    for i in range(burst_len + 1):
        value, last, byte_strobe = yield from read_from_stream(axi.write_data, ("payload", "last", "byte_strobe"))
        if i == burst_len:
            assert last
        else:
            assert not last
        if byte_strobe != 0:
            print(value, byte_strobe, last)
            memory[addr + i * axi.data_bytes] = value
            accepted += 1
    write_to_stream(axi.write_response, resp=Response.OKAY)

    return memory, accepted


class TestSimAxiWriter(unittest.TestCase):
    def test_buffer_change(self, data_len=50):
        axi = AxiEndpoint(addr_bits=32, data_bits=64, master=False, lite=False, id_bits=12)

        ringbuffer = RingBufferAddressStorage(0x1000, 2, base_address=0)
        stream_source = PacketizedStream(64)

        dut = AxiBufferWriter(ringbuffer, stream_source, axi, fifo_depth=data_len)

        gold = {}

        def testbench():
            gold_gen = {
                "current_buffer": 0,
                "current_address": ringbuffer.buffer_base_list[0]
            }

            def put_data(data, last):
                gold[gold_gen["current_address"]] = data
                # print("w", gold_gen["current_address"], data)
                gold_gen["current_address"] += axi.data_bytes
                yield from write_to_stream(stream_source, payload=data, last=last)
                if last:
                    gold_gen["current_buffer"] = (gold_gen["current_buffer"] + 1) % len(ringbuffer.buffer_base_list)
                    gold_gen["current_address"] = ringbuffer.buffer_base_list[gold_gen["current_buffer"]]

            # first, fill in some data:
            for i in range(data_len):
                yield from put_data(i, last=i % 5 == 0)
                # if i % 7 == 0:
                #     yield from do_nothing()

        def axi_process():
            memory = {}
            accepted = 0
            while accepted < data_len:
                memory_fragment, accepted_frag = (yield from answer_write_burst(axi))
                memory.update(memory_fragment)
                accepted += accepted_frag
                yield
            self.assertEqual(gold, memory)

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.add_process(axi_process, "sync")
        platform.sim(dut, testbench)

    def test_basic(self, data_len=50):
        axi = AxiEndpoint(addr_bits=32, data_bits=64, master=False, lite=False, id_bits=12)

        ringbuffer = RingBufferAddressStorage(0x1000, 2, base_address=0)
        stream_source = PacketizedStream(64)

        dut = AxiBufferWriter(ringbuffer, stream_source, axi, fifo_depth=data_len)

        def write_process():
            for round in range(4):
                for i in range(data_len):
                    yield from write_to_stream(stream_source, payload=i + round)

        def testbench():
            remaining = {}
            for round in range(4):
                print("r", round, remaining)
                memory = remaining
                while len(memory) < data_len:
                    print("m", len(memory), memory)
                    written, accepted = (yield from answer_write_burst(axi))
                    print("w", len(written), written)
                    taken = []
                    for k, v in written.items():
                        if len(memory) < data_len:
                            print("p", len(memory), k, v)
                            memory[k] = v
                            taken.append(k)
                    remaining = {}
                    for k, v in written.items():
                        if k not in taken:
                            remaining[k] = v
                    print("m", len(memory), memory)
                self.assertEqual({
                    (ringbuffer.buffer_base_list[0] + i * axi.data_bytes + round * 400): (i + round)
                    for i in range(data_len)
                }, memory)
                yield from do_nothing(10)

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.add_process(write_process, "sync")
        platform.sim(dut, testbench)
