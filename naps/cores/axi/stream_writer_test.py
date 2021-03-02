import unittest
from naps import SimPlatform, BasicStream
from naps.stream import verify_stream_output_contract, LegalStreamSource, write_to_stream
from . import AxiEndpoint, answer_write_burst
from .stream_writer import AxiWriter, AxiWriterBurster, StreamPacketizer


class TestAxiWriter(unittest.TestCase):
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

    def test_burster_address_output_stream_contract(self):
        data_input = BasicStream(64)
        address_input = BasicStream(32)

        dut = AxiWriterBurster(address_input, data_input)
        verify_stream_output_contract(
            dut, stream_output=dut.address_output,
            support_modules=(LegalStreamSource(data_input), LegalStreamSource(address_input))
        )

    def test_packetizer_output_stream_contract(self):
        length_input = BasicStream(4)
        data_input = BasicStream(64)

        dut = StreamPacketizer(length_input, data_input)
        verify_stream_output_contract(
            dut, support_modules=(LegalStreamSource(data_input), LegalStreamSource(length_input))
        )

    def test_burster_data_output_stream_contract(self):
        data_input = BasicStream(64)
        address_input = BasicStream(32)

        dut = AxiWriterBurster(address_input, data_input)
        verify_stream_output_contract(
            dut, stream_output=dut.data_output,
            support_modules=(LegalStreamSource(data_input), LegalStreamSource(address_input))
        )
