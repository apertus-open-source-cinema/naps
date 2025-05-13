import unittest
import random
from amaranth import *
from amaranth.lib import wiring, stream
from amaranth.lib.wiring import Component, Out, In

from naps import SimPlatform, write_packet_to_stream, read_packet_from_stream, BufferedSyncStreamFIFO, \
    Packet, FormalPlatform
from naps.stream.formal_util import verify_stream_output_contract, LegalStreamSource, StreamOutputAssertSpec
from . import LastWrapper


class LastWrapperContract(Component):
    to_last_wrapper: Out(stream.Signature(Packet(32)))
    from_last_wrapper: In(stream.Signature(Packet(32)))

    def __init__(self, packets=(1, 27, 3, 5)):
        super().__init__()
        self.last_data = Array((i == l - 1) for l in packets for i in range(l))
        self.n_packets = len(packets)

    def elaborate(self, platform):
        m = Module()

        write_ctr = Signal(range(len(self.last_data)))
        with m.If(write_ctr < len(self.last_data) - 1):
            m.d.comb += self.to_last_wrapper.valid.eq(1)
            m.d.comb += self.to_last_wrapper.p.last.eq(self.last_data[write_ctr])
            with m.If(self.to_last_wrapper.ready):
                m.d.sync += write_ctr.eq(write_ctr + 1)

        read_ctr = Signal.like(write_ctr)
        with m.If(read_ctr < len(self.last_data) - 1):
            m.d.comb += self.from_last_wrapper.ready.eq(1)
            with m.If(self.from_last_wrapper.valid):
                m.d.sync += read_ctr.eq(read_ctr + 1)
                m.d.comb += Assert(self.from_last_wrapper.p.last == self.last_data[read_ctr])

        return m


class LastWrapperTest(unittest.TestCase):
    def test_randomized(self):
        platform = SimPlatform()

        dut = Module()
        dut.submodules.fifo = fifo = BufferedSyncStreamFIFO(32, 10)
        dut.submodules.last_wrapper = last_wrapper = LastWrapper(32, 32, last_rle_bits=4)
        wiring.connect(dut, fifo.input, last_wrapper.to_core)
        wiring.connect(dut, fifo.output, last_wrapper.from_core)

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
                yield from write_packet_to_stream(last_wrapper.input, packet)
        platform.add_process(writer_process, "sync")

        def reader_process():
            read_packets = []
            while len(read_packets) < len(test_packets):
                read = (yield from read_packet_from_stream(last_wrapper.output))
                read_packets.append(read)
                print([len(p) for p in read_packets])

            self.assertEqual(read_packets, test_packets)
        platform.add_process(reader_process, "sync")

        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut)

    def test_long_fifo(self):
        platform = SimPlatform()

        dut = Module()
        dut.submodules.fifo = fifo = BufferedSyncStreamFIFO(32, 200)
        dut.submodules.last_wrapper = last_wrapper = LastWrapper(32, 32, last_rle_bits=10)
        wiring.connect(dut, fifo.input, last_wrapper.to_core)
        wiring.connect(dut, fifo.output, last_wrapper.from_core)

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
                yield from write_packet_to_stream(last_wrapper.input, packet)
        platform.add_process(writer_process, "sync")

        def reader_process():
            read_packets = []
            while len(read_packets) < len(test_packets):
                read = (yield from read_packet_from_stream(last_wrapper.output))
                read_packets.append(read)
                print([len(p) for p in read_packets])

            self.assertEqual(read_packets, test_packets)
        platform.add_process(reader_process, "sync")

        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut)

    def test_last_wrapper_contract(self):
        plat = FormalPlatform()
        m = Module()

        m.submodules.fifo = fifo = BufferedSyncStreamFIFO(32, 10)
        m.submodules.last_wrapper = last_wrapper = LastWrapper(32, 32)
        wiring.connect(m, fifo.input, last_wrapper.to_core)
        wiring.connect(m, fifo.output, last_wrapper.from_core)

        m.submodules.contract = contract = LastWrapperContract()
        wiring.connect(m, contract.to_last_wrapper, last_wrapper.input)
        wiring.connect(m, contract.from_last_wrapper, last_wrapper.output)

        plat.run_formal(m, mode="bmc", depth=10)

    def test_output_stream_contract(self):
        plat = FormalPlatform()
        m = Module()
        m.submodules.legal_input = legal_stream_source = LegalStreamSource(Packet(32))

        m.submodules.fifo = fifo = BufferedSyncStreamFIFO(32, 10)
        m.submodules.last_wrapper = last_wrapper = LastWrapper(32, 32, last_rle_bits=3)
        wiring.connect(m, fifo.input, last_wrapper.to_core)
        wiring.connect(m, fifo.output, last_wrapper.from_core)

        wiring.connect(m, last_wrapper.input, legal_stream_source.output)

        #m.submodules.output = stream_spec = StreamOutputAssertSpec(Packet(32))
       # wiring.connect(m, last_wrapper.output, stream_spec.input)

        m.submodules.output = stream_spec = StreamOutputCoverSpec(Packet(32))
        wiring.connect(m, last_wrapper.output, stream_spec.input)

        plat.run_formal(m)

    def test_core_output_stream_contract(self):
        m = Module()



        input_stream = PacketizedStream(32)
        device_input_stream: BasicStream
        def core_producer(i):
            nonlocal device_input_stream
            device_input_stream = i
            return LegalStreamSource(i.clone())
        dut = LastWrapper(input_stream, core_producer, last_rle_bits=3)
        verify_stream_output_contract(dut, stream_output=device_input_stream, support_modules=(LegalStreamSource(input_stream),))
