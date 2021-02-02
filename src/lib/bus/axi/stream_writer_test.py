import unittest

from lib.bus.axi.axi_endpoint import AxiEndpoint
from lib.bus.axi.sim_util import answer_write_burst
from lib.bus.axi.stream_writer import AxiWriter
from lib.bus.stream.sim_util import write_to_stream
from lib.bus.stream.stream import BasicStream
from util.sim import SimPlatform, do_nothing


class TestSimAxiWriter(unittest.TestCase):
    def test_basic(self):
        platform = SimPlatform()
        axi = AxiEndpoint(addr_bits=32, data_bits=64, lite=False, id_bits=12)

        data_stream = BasicStream(64)
        address_stream = BasicStream(32)

        write_sequence = [
            (0, 1),
            (0, 2),
            (0, 3),
            (0, 4),
            (1, 5),
            (2, 6),

            *[(a, a) for a in range(10, 1000, 8)],

            (1000, 1),
            (1000, 2),
            (1000, 3),
            (1000, 4),
            (1001, 5),
            (1002, 6),
        ]

        golden_memory = {}
        for addr, data in write_sequence:
            golden_memory[addr] = data

        dut = AxiWriter(address_stream, data_stream, axi)

        def write_address_process():
            for addr, data in write_sequence:
                yield from write_to_stream(address_stream, payload=addr)
        platform.add_process(write_address_process, "sync")

        def write_data_process():
            for addr, data in write_sequence:
                yield from write_to_stream(data_stream, payload=data)
        platform.add_process(write_data_process, "sync")

        def axi_answer_process():
            memory = {}
            while len(memory) < len(golden_memory):
                # print("m", len(memory), memory)
                written, accepted = (yield from answer_write_burst(axi))
                print("w", len(written), written)
                memory.update(written)
            self.assertEqual(golden_memory, memory)
        platform.add_process(axi_answer_process, "sync")

        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut)
