import random
import unittest
from nmigen import *
from nmigen.sim import Passive
from naps import SimPlatform, do_nothing, BasicStream, PacketizedStream, read_from_stream, write_to_stream
from naps.stream import LegalStreamSource, verify_stream_output_contract
from naps.cores import BufferedSyncStreamFIFO, StreamTee, StreamGearbox, SimpleStreamGearbox


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
            yield from write_to_stream(input, payload=0b00_10_00_01, last=1)
            yield from write_to_stream(input, payload=0b10_00_01_00, last=0)

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

    def test_gearbox_48_to_12_last(self):
        input = PacketizedStream(48)
        dut = StreamGearbox(input, 12)

        def writer():
            yield from write_to_stream(input, payload=0b000000000100_000000000010_000000000001_100000000000, last=1)
            yield from write_to_stream(input, payload=0b000001000000_000000100000_000000010000_000000001000, last=0)

        def reader():
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b100000000000, 0))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b000000000001, 0))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b000000000010, 0))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b000000000100, 1))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b000000001000, 0))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b000000010000, 0))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b000000100000, 0))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b000001000000, 0))

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.add_process(writer, "sync")
        platform.add_process(reader, "sync")
        platform.sim(dut)

    def test_gearbox_12_to_48_to_64(self):
        m = Module()
        platform = SimPlatform()
        input = BasicStream(12)

        tee = m.submodules.tee = StreamTee(input)
        gear_12_to_48 = m.submodules.gear_12_to_48 = StreamGearbox(tee.get_output(), 48)
        gear_48_to_64 = m.submodules.gear_48_to_64 = StreamGearbox(gear_12_to_48.output, 64)

        gear_12_to_64 = m.submodules.gear_12_to_64 = StreamGearbox(tee.get_output(), 64)

        def writer():
            yield Passive()
            random.seed(0)
            while True:
                yield from write_to_stream(input, payload=random.randrange(0, 2**12))
        platform.add_process(writer, "sync")

        def reader():
            for _ in range(100):
                a = yield from read_from_stream(gear_12_to_64.output)
                b = yield from read_from_stream(gear_48_to_64.output)
                print(f"{a:064b}")
                self.assertEqual(a, b)
        platform.add_process(reader, "sync")

        platform.add_sim_clock("sync", 100e6)
        platform.sim(m)

    def test_dont_loose_data(self):
        input = BasicStream(16)
        dut = StreamGearbox(input, 8)

        def writer():
            for i in range(0, 100, 2):
                yield from write_to_stream(input, payload=(((i + 1) << 8) | i))
                if i % 7 == 0:
                    yield from do_nothing()

        def reader():
            for i in range(100):
                got = (yield from read_from_stream(dut.output, extract="payload"))
                print(got)
                self.assertEqual(got, i)
                if i % 3 == 0:
                    yield from do_nothing()

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.add_process(writer, "sync")
        platform.add_process(reader, "sync")
        platform.sim(dut)

    def test_dont_loose_last_8_to_4(self):
        input = PacketizedStream(8)
        dut = StreamGearbox(input, 4)

        def writer():
            last_count_gold = 0
            for i in range(50):
                last = (i % 5 == 0)
                last_count_gold += last
                yield from write_to_stream(input, payload=0, last=last)
                if i % 7 == 0:
                    yield from do_nothing()
            self.assertEqual(last_count_gold, 10)

        def reader():
            last_count = 0
            for i in range(100):
                last = (yield from read_from_stream(dut.output, extract="last"))
                last_count += last
                if i % 10 == 1:
                    assert last
                else:
                    assert not last
                if i % 3 == 0:
                    yield from do_nothing()
            self.assertEquals(last_count, 10)

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.add_process(writer, "sync")
        platform.add_process(reader, "sync")
        platform.sim(dut)

    def test_dont_loose_last_16_to_4(self):
        input = PacketizedStream(16)
        dut = StreamGearbox(input, 4)

        def writer():
            last_count_gold = 0
            for i in range(50):
                last = (i % 5 == 0)
                last_count_gold += last
                yield from write_to_stream(input, payload=0, last=(i % 5 == 0))
                if i % 3 == 0:
                    yield from do_nothing()
            self.assertEqual(last_count_gold, 10)

        def reader():
            last_count = 0
            for i in range(200):
                last_count += (yield from read_from_stream(dut.output, extract="last"))
                if i % 10 == 0:
                    yield from do_nothing()
            self.assertEquals(last_count, 10)

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.add_process(writer, "sync")
        platform.add_process(reader, "sync")
        platform.sim(dut)

    def test_gearbox_automated_fifo(self):
        def string_generator(string, chunk_size):
            last = 0
            while True:
                to_yield = ""
                for _ in range(chunk_size):
                    try:
                        to_yield += string[last]
                    except IndexError:
                        return
                    last += 1
                yield "".join(reversed(to_yield))

        def gold_gen(input_width, output_width, output_amount=10):
            bit_sequence = ""
            for i in range(output_amount):
                bit_sequence += "{{:0{}b}}".format(input_width).format(i % (2 ** input_width))
            return (
                [int(s, 2) for s in string_generator(bit_sequence, input_width)],
                [int(s, 2) for s in string_generator(bit_sequence, output_width)]
            )

        def test_gearbox(input_width, output_width):
            input = PacketizedStream(input_width)
            m = Module()
            fifo_in = m.submodules.fifo_in = BufferedSyncStreamFIFO(input, 100)
            gearbox = m.submodules.gearbox = StreamGearbox(fifo_in.output, output_width)
            fifo_out = m.submodules.fifo_out = BufferedSyncStreamFIFO(gearbox.output, 100)

            input_data, output_data = gold_gen(input_width, output_width)

            def writer():
                for v in input_data:
                    yield from write_to_stream(input, payload=v)

            def reader():
                for i, v in enumerate(output_data):
                    read = (yield from read_from_stream(fifo_out.output))
                    self.assertEqual(read, v)

            platform = SimPlatform()
            platform.add_sim_clock("sync", 100e6)
            platform.add_process(writer, "sync")
            platform.add_process(reader, "sync")
            platform.sim(m)

        test_gearbox(8, 4)
        test_gearbox(7, 3)
        test_gearbox(48, 12)

        for input_width in range(1, 100, 7):
            for output_width in range(1, 100, 3):
                test_gearbox(input_width, output_width)

    def test_output_stream_contract(self):
        input = BasicStream(7)
        verify_stream_output_contract(StreamGearbox(input, 3))


class TestSimpleGearbox(unittest.TestCase):
    def test_simple_gearbox_8_to_4_last(self):
        input = PacketizedStream(8)
        dut = SimpleStreamGearbox(input, 4)

        def writer():
            yield from write_to_stream(input, payload=0b00_10_00_01, last=1)
            yield from write_to_stream(input, payload=0b10_00_01_00, last=0)

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

    def test_simple_gearbox_48_to_12_last(self):
        input = PacketizedStream(48)
        dut = SimpleStreamGearbox(input, 12)

        def writer():
            yield from write_to_stream(input, payload=0b000000000100_000000000010_000000000001_100000000000, last=1)
            yield from write_to_stream(input, payload=0b000001000000_000000100000_000000010000_000000001000, last=0)

        def reader():
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b100000000000, 0))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b000000000001, 0))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b000000000010, 0))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b000000000100, 1))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b000000001000, 0))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b000000010000, 0))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b000000100000, 0))
            self.assertEqual((yield from read_from_stream(dut.output, extract=("payload", "last"))), (0b000001000000, 0))

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.add_process(writer, "sync")
        platform.add_process(reader, "sync")
        platform.sim(dut)

    def test_simple_gearbox_dont_loose_last_16_to_4(self):
        input = PacketizedStream(16)
        dut = SimpleStreamGearbox(input, 4)

        def writer():
            last_count_gold = 0
            for i in range(50):
                last = (i % 5 == 0)
                last_count_gold += last
                yield from write_to_stream(input, payload=0, last=(i % 5 == 0))
                if i % 3 == 0:
                    yield from do_nothing()
            self.assertEqual(last_count_gold, 10)

        def reader():
            last_count = 0
            for i in range(200):
                last_count += (yield from read_from_stream(dut.output, extract="last"))
                if i % 10 == 0:
                    yield from do_nothing()
            self.assertEquals(last_count, 10)

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.add_process(writer, "sync")
        platform.add_process(reader, "sync")
        platform.sim(dut)

    def test_output_stream_contract(self):
        input = BasicStream(8)
        verify_stream_output_contract(SimpleStreamGearbox(input, 4), support_modules=(LegalStreamSource(input),))
