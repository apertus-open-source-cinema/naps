import unittest

from nmigen import *

from naps import SimPlatform, verify_stream_output_contract
from naps.cores.debug.packet_console import ConsolePacketSource, ConsolePacketSink


class StreamMemoryTest(unittest.TestCase):
    def test_roundtrip_complex(self):
        platform = SimPlatform()

        m = Module()

        source = m.submodules.source = ConsolePacketSource()
        sink = m.submodules.sink = ConsolePacketSink(source.output)

        read = Signal()
        read_ = Signal()
        m.d.comb += read_.eq(read)
        write = Signal()
        write_ = Signal()
        m.d.comb += write_.eq(write)

        def testbench():
            def write_packet(packet):  # this is a modified version of the original driver code
                yield write.eq(1)
                assert (yield source.done) == 1
                yield
                for i, word in enumerate(packet):
                    yield source.memory.memory[i].eq(word)
                yield
                yield source.packet_length.eq(len(packet) - 1)
                yield
                yield source.reset.eq(not (yield source.reset))
                yield
                yield write.eq(0)

            def read_packet():  # this is a modified version of the original driver code
                yield read.eq(1)
                if not (yield sink.packet_done):
                    return None
                yield
                to_return = []
                print((yield sink.write_pointer))
                for i in range((yield sink.write_pointer)):
                    to_return.append((yield sink.memory.memory[i]))
                yield
                yield sink.reset.eq(not (yield sink.reset))
                yield
                yield read.eq(0)
                return to_return

            test_packet = [10, 20, 30, 40, 0]
            yield from write_packet(test_packet)
            for i in range(20):
                yield
            yield from write_packet(test_packet)
            for i in range(20):
                yield
            self.assertEqual(test_packet, (yield from read_packet()))
            for i in range(20):
                yield
            self.assertEqual(test_packet, (yield from read_packet()))

        platform.add_sim_clock("sync", 100e6)
        platform.sim(m, testbench)

    def test_source_output_stream_contract(self):
        dut = ConsolePacketSource()
        verify_stream_output_contract(dut)
