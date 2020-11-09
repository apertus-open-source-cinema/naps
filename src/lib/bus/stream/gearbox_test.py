import unittest

from lib.bus.stream.gearbox import StreamGearbox
from lib.bus.stream.sim_util import read_from_stream, write_to_stream
from lib.bus.stream.stream import BasicStream
from util.sim import SimPlatform


class TestGearbox(unittest.TestCase):
    def test_gearbox_basic(self):
        input = BasicStream(7)
        dut = StreamGearbox(input, 3)

        def writer():
            yield from write_to_stream(input, payload=0b001_010_1)
            yield from write_to_stream(input, payload=0b00_011_11)
            yield from write_to_stream(input, payload=0b0_111_000)

        def reader():
            self.assertEquals((yield from read_from_stream(dut.output)), 0b001)
            self.assertEquals((yield from read_from_stream(dut.output)), 0b010)
            self.assertEquals((yield from read_from_stream(dut.output)), 0b100)
            self.assertEquals((yield from read_from_stream(dut.output)), 0b011)
            self.assertEquals((yield from read_from_stream(dut.output)), 0b110)
            self.assertEquals((yield from read_from_stream(dut.output)), 0b111)
            self.assertEquals((yield from read_from_stream(dut.output)), 0b000)

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.add_process(reader, "sync")
        platform.add_process(writer, "sync")
        platform.sim(dut)