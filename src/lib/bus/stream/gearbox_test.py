import unittest

from lib.bus.stream.gearbox import StreamGearbox
from lib.bus.stream.sim_util import read_from_stream, write_to_stream
from lib.bus.stream.stream import BasicStream, PacketizedStream
from util.sim import SimPlatform

class TestGearbox(unittest.TestCase):
    def test_gearbox_7_to_3(self):
        input = BasicStream(7)
        dut = StreamGearbox(input, 3)

        def writer():
            yield from write_to_stream(input, payload=0b0_010_001)
            yield from write_to_stream(input, payload=0b10_011_10)
            yield from write_to_stream(input, payload=0b000_111_1)

        def reader():
            self.assertEqual((yield from read_from_stream(dut.output)), 0b001)
            self.assertEqual((yield from read_from_stream(dut.output)), 0b010)
            self.assertEqual((yield from read_from_stream(dut.output)), 0b100)
            self.assertEqual((yield from read_from_stream(dut.output)), 0b011)
            self.assertEqual((yield from read_from_stream(dut.output)), 0b110)
            self.assertEqual((yield from read_from_stream(dut.output)), 0b111)
            self.assertEqual((yield from read_from_stream(dut.output)), 0b000)

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.add_process(writer, "sync")
        platform.add_process(reader, "sync")
        platform.sim(dut)

    def test_gearbox_3_to_7(self):
        input = BasicStream(3)
        dut = StreamGearbox(input, 7)

        def writer():
            yield from write_to_stream(input, payload=0b001)
            yield from write_to_stream(input, payload=0b010)
            yield from write_to_stream(input, payload=0b100)
            yield from write_to_stream(input, payload=0b011)
            yield from write_to_stream(input, payload=0b110)
            yield from write_to_stream(input, payload=0b111)
            yield from write_to_stream(input, payload=0b000)

        def reader():
            self.assertEqual((yield from read_from_stream(dut.output)), 0b0_010_001)
            self.assertEqual((yield from read_from_stream(dut.output)), 0b10_011_10)
            self.assertEqual((yield from read_from_stream(dut.output)), 0b000_111_1)

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.add_process(writer, "sync")
        platform.add_process(reader, "sync")
        platform.sim(dut)

    def test_gearbox_4_to_8_last(self):
        input = PacketizedStream(4)
        dut = StreamGearbox(input, 8)

        def writer():
            yield from write_to_stream(input, payload=0b0001, last=0)
            yield from write_to_stream(input, payload=0b0010, last=1)
            yield from write_to_stream(input, payload=0b0100, last=0)
            yield from write_to_stream(input, payload=0b1000, last=0)

        def reader():
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b0010_0001, 1))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b1000_0100, 0))

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.add_process(writer, "sync")
        platform.add_process(reader, "sync")
        platform.sim(dut)

    def test_gearbox_8_to_4_last(self):
        input = PacketizedStream(8)
        dut = StreamGearbox(input, 4)

        def writer():
            yield from write_to_stream(input, payload=0b0010_0001, last=1)
            yield from write_to_stream(input, payload=0b1000_0100, last=0)

        def reader():
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b0001, 0))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b0010, 1))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b0100, 0))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b1000, 0))

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.add_process(writer, "sync")
        platform.add_process(reader, "sync")
        platform.sim(dut)
