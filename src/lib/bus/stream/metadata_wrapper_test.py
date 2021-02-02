import unittest
import random

from lib.bus.stream.fifo import BufferedSyncStreamFIFO
from lib.bus.stream.metadata_wrapper import LastWrapper
from lib.bus.stream.sim_util import write_packet_to_stream, read_packet_from_stream
from lib.bus.stream.stream import PacketizedStream
from util.sim import SimPlatform


class MetadataWrapperTest(unittest.TestCase):
    def test_last_wrapper_randomized(self):
        platform = SimPlatform()

        input_stream = PacketizedStream(32)
        dut = LastWrapper(input_stream, lambda i: BufferedSyncStreamFIFO(i, 100), last_fifo_depth=2, last_rle_bits=4)

        random.seed(0)
        test_packets = [
            [random.randint(0, 2**32) for _ in range(random.randint(1, 1000))]
            for _ in range(1)
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

            self.assertEqual(read_packets, test_packets)
        platform.add_process(reader_process, "sync")

        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut)