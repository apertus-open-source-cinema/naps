import unittest

from nmigen import *

from lib.bus.axi.sim_util import axi_ram_sim_model
from lib.bus.stream.sim_util import write_packet_to_stream, read_packet_from_stream
from lib.bus.stream.stream import PacketizedStream
from lib.dram_packet_ringbuffer.stream_if import DramPacketRingbufferStreamWriter, DramPacketRingbufferStreamReader
from util.sim import SimPlatform


class StreamIfTest(unittest.TestCase):
    def test_integration(self):
        plat = SimPlatform()
        m = Module()
        writer_axi_port, reader_axi_port = axi_ram_sim_model(plat)

        input_stream = PacketizedStream(64)
        writer = m.submodules.writer = DramPacketRingbufferStreamWriter(input_stream, max_packet_size=1000 * 8, n_buffers=4, axi=writer_axi_port)
        reader = m.submodules.reader = DramPacketRingbufferStreamReader(writer, axi=reader_axi_port)

        def testbench():
            test_packets = [
                [0 for _ in range(900)],
                [i for i in range(900)]
            ]

            for p in test_packets:
                yield from write_packet_to_stream(input_stream, p)

            read_packets = []
            while len(read_packets) < len(test_packets):
                read = yield from read_packet_from_stream(reader.output)
                read_packets.append(read)

            self.assertEqual(read_packets, test_packets)

        plat.add_sim_clock("sync", 100e6)
        plat.sim(m, testbench)
