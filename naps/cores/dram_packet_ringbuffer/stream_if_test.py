import unittest
from nmigen import *
from naps import SimPlatform
from naps.cores.axi import axi_ram_sim_model
from naps.stream import PacketizedStream, write_packet_to_stream, read_packet_from_stream
from . import DramPacketRingbufferCpuReader, DramPacketRingbufferStreamWriter, DramPacketRingbufferStreamReader


class StreamIfTest(unittest.TestCase):
    def test_integration(self):
        plat = SimPlatform()
        m = Module()
        writer_axi_port, reader_axi_port = axi_ram_sim_model(plat)

        input_stream = PacketizedStream(64)
        writer = m.submodules.writer = DramPacketRingbufferStreamWriter(input_stream, base_address=0, max_packet_size=10000, n_buffers=4, axi=writer_axi_port)
        reader = m.submodules.reader = DramPacketRingbufferStreamReader(writer, axi=reader_axi_port)
        cpu_reader = m.submodules.cpu_reader = DramPacketRingbufferCpuReader(writer)

        def testbench():
            test_packets = [
                [0 for _ in range(100)],
                [i for i in range(100)]
            ]

            for p in test_packets:
                yield from write_packet_to_stream(input_stream, p)

            read_packets = []
            while len(read_packets) < len(test_packets):
                read = yield from read_packet_from_stream(reader.output)
                read_packets.append(read)

            self.assertEqual(read_packets, test_packets)
            self.assertEqual((yield writer.buffer_level_list[0]), 800)
            self.assertEqual((yield writer.buffer_level_list[1]), 800)

            self.assertEqual((yield cpu_reader.buffer0_level), 800)
            self.assertEqual((yield cpu_reader.buffer1_level), 800)

        plat.add_sim_clock("sync", 100e6)
        plat.sim(m, testbench)
