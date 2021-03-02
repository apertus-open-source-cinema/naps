import unittest
from nmigen.sim import Passive
from naps import SimPlatform, BasicStream, write_to_stream, read_from_stream
from naps.stream.formal_util import verify_stream_output_contract, LegalStreamSource
from naps.cores.axi import AxiEndpoint, answer_read_burst
from .stream_reader import AxiReader, AxiReaderBurster


class TestAxiReader(unittest.TestCase):
    def test_basic(self):
        platform = SimPlatform()

        memory = {i: i + 100 for i in range(1000)}
        read_sequence = [
            0,
            100,
            108,
            116,
            2,
            7,
            *[i + 100 for i in range(0, 400, 8)],
            0,
            100,
            108,
            116,
            2,
            7,
        ]
        golden_read_result = [memory[addr] for addr in read_sequence]

        axi = AxiEndpoint(addr_bits=32, data_bits=64, lite=False, id_bits=12)
        address_stream = BasicStream(32)
        dut = AxiReader(address_stream, axi)

        def write_address_process():
            for addr in read_sequence:
                yield from write_to_stream(address_stream, payload=addr)
        platform.add_process(write_address_process, "sync")

        def read_data_process():
            read_result = []
            while len(read_result) < len(golden_read_result):
                read = yield from read_from_stream(dut.output)
                read_result.append(read)
            self.assertEqual(read_result, golden_read_result)
        platform.add_process(read_data_process, "sync")

        def axi_answer_process():
            yield Passive()
            while True:
                yield from answer_read_burst(axi, memory)
        platform.add_process(axi_answer_process, "sync")

        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut)

    def test_reader_stream_output(self):
        axi = AxiEndpoint(addr_bits=32, data_bits=64, lite=False, id_bits=12)
        verify_stream_output_contract(
            AxiReader(BasicStream(32), axi),
            support_modules=(LegalStreamSource(axi.read_data),)
        )

    def test_burster_stream_output(self):
        i = BasicStream(32)
        verify_stream_output_contract(
            AxiReaderBurster(i),
            support_modules=(LegalStreamSource(i),)
        )
