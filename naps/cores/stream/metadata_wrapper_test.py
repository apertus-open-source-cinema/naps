import unittest
import random
from nmigen import *
from nmigen.hdl.ast import Assert, Initial, Assume
from naps import SimPlatform, PacketizedStream, BasicStream, assert_formal, write_packet_to_stream, read_packet_from_stream, BufferedSyncStreamFIFO
from naps.stream.formal_util import verify_stream_output_contract, LegalStreamSource
from . import LastWrapper, GenericMetadataWrapper


class LastWrapperContract(Elaboratable):
    def __init__(self, last_wrapper, packets=(1, 27, 3, 5)):
        self.last_wrapper = last_wrapper
        self.last_data = Array((i == l - 1) for l in packets for i in range(l))
        self.n_packets = len(packets)

    def elaborate(self, platform):
        m = Module()

        m.submodules.last_wrapper = self.last_wrapper

        lw_input = self.last_wrapper.input
        lw_output = self.last_wrapper.output
        with m.If(Initial()):
            m.d.comb += Assume(ResetSignal())

        write_ctr = Signal(range(len(self.last_data)))
        with m.If(write_ctr < len(self.last_data) - 1):
            m.d.comb += lw_input.valid.eq(1)
            m.d.comb += lw_input.last.eq(self.last_data[write_ctr])
            with m.If(lw_input.ready):
                m.d.sync += write_ctr.eq(write_ctr + 1)

        read_ctr = Signal.like(write_ctr)
        with m.If(read_ctr < len(self.last_data) - 1):
            m.d.comb += lw_output.ready.eq(1)
            with m.If(lw_output.valid):
                m.d.sync += read_ctr.eq(read_ctr + 1)
                with m.If(~Initial()):
                    m.d.comb += Assert(lw_output.last == self.last_data[read_ctr])

        return m


class LastWrapperTest(unittest.TestCase):
    def test_randomized(self):
        platform = SimPlatform()

        input_stream = PacketizedStream(32)
        dut = LastWrapper(input_stream, lambda i: BufferedSyncStreamFIFO(i, 10), last_rle_bits=4)

        random.seed(0)
        test_packets = [
            [random.randint(0, 2**32) for _ in range(12)],
            [random.randint(0, 2**32) for _ in range(24)],
            [random.randint(0, 2**32) for _ in range(1)],
            [random.randint(0, 2**32) for _ in range(1000)],
            [random.randint(0, 2**32) for _ in range(1000)],
            [random.randint(0, 2 ** 32) for _ in range(12)],
            [random.randint(0, 2 ** 32) for _ in range(1000)],
        ]

        def writer_process():
            for packet in test_packets:
                yield from write_packet_to_stream(input_stream, packet)
        platform.add_process(writer_process, "sync")

        def reader_process():
            read_packets = []
            while len(read_packets) < len(test_packets):
                read = (yield from read_packet_from_stream(dut.output))
                read_packets.append(read)
                print([len(p) for p in read_packets])

            self.assertEqual(read_packets, test_packets)
        platform.add_process(reader_process, "sync")

        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut)

    def test_long_fifo(self):
        platform = SimPlatform()

        input_stream = PacketizedStream(32)
        dut = LastWrapper(input_stream, lambda i: BufferedSyncStreamFIFO(i, 200), last_rle_bits=10)

        random.seed(0)
        test_packets = [
            [random.randint(0, 2**32) for _ in range(12)],
            [random.randint(0, 2**32) for _ in range(24)],
            [random.randint(0, 2**32) for _ in range(1)],
            [random.randint(0, 2**32) for _ in range(1000)],
            [random.randint(0, 2**32) for _ in range(1000)],
            [random.randint(0, 2 ** 32) for _ in range(12)],
            [random.randint(0, 2 ** 32) for _ in range(1000)],
        ]

        def writer_process():
            for packet in test_packets:
                yield from write_packet_to_stream(input_stream, packet)
        platform.add_process(writer_process, "sync")

        def reader_process():
            read_packets = []
            while len(read_packets) < len(test_packets):
                read = (yield from read_packet_from_stream(dut.output))
                read_packets.append(read)
                print([len(p) for p in read_packets])

            self.assertEqual(read_packets, test_packets)
        platform.add_process(reader_process, "sync")

        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut)

    def test_last_wrapper_contract(self):
        dut = LastWrapperContract(LastWrapper(PacketizedStream(32), lambda i: BufferedSyncStreamFIFO(i, 10)))
        assert_formal(dut, mode="hybrid", depth=10)

    def test_output_stream_contract(self):
        input_stream = PacketizedStream(32)
        dut = LastWrapper(input_stream, lambda i: BufferedSyncStreamFIFO(i, 10), last_rle_bits=3)
        verify_stream_output_contract(dut, support_modules=(LegalStreamSource(input_stream),))

    def test_core_output_stream_contract(self):
        input_stream = PacketizedStream(32)
        device_input_stream: BasicStream
        def core_producer(i):
            nonlocal device_input_stream
            device_input_stream = i
            return LegalStreamSource(i.clone())
        dut = LastWrapper(input_stream, core_producer, last_rle_bits=3)
        verify_stream_output_contract(dut, stream_output=device_input_stream, support_modules=(LegalStreamSource(input_stream),))


class GenericMetadataWrapperTest(unittest.TestCase):
    def test_randomized(self):
        platform = SimPlatform()

        input_stream = PacketizedStream(32)
        dut = GenericMetadataWrapper(input_stream, lambda i: BufferedSyncStreamFIFO(i, 10, output_stream_name="core_output"), fifo_depth=11)

        random.seed(0)
        test_packets = [
            [random.randint(0, 2**32) for _ in range(12)],
            [random.randint(0, 2**32) for _ in range(24)],
            [random.randint(0, 2**32) for _ in range(1)],
            [random.randint(0, 2**32) for _ in range(1000)],
            [random.randint(0, 2**32) for _ in range(1000)],
            [random.randint(0, 2 ** 32) for _ in range(12)],
            [random.randint(0, 2 ** 32) for _ in range(1000)],
        ]

        def writer_process():
            for packet in test_packets:
                yield from write_packet_to_stream(input_stream, packet)
        platform.add_process(writer_process, "sync")

        def reader_process():
            read_packets = []
            while len(read_packets) < len(test_packets):
                read = (yield from read_packet_from_stream(dut.output))
                read_packets.append(read)
                print([len(p) for p in read_packets])

            self.assertEqual(read_packets, test_packets)
        platform.add_process(reader_process, "sync")

        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut)

    def test_output_stream_contract(self):
        input_stream = PacketizedStream(32)
        dut = GenericMetadataWrapper(input_stream, lambda i: BufferedSyncStreamFIFO(i, 10))
        verify_stream_output_contract(dut, support_modules=(LegalStreamSource(input_stream),))

    def test_core_output_stream_contract(self):
        input_stream = PacketizedStream(32)
        device_input_stream: BasicStream
        def core_producer(i):
            nonlocal device_input_stream
            device_input_stream = i
            return LegalStreamSource(i.clone())
        dut = GenericMetadataWrapper(input_stream, core_producer)
        verify_stream_output_contract(dut, stream_output=device_input_stream, support_modules=(LegalStreamSource(input_stream),))
