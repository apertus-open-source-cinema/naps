import unittest

from nmigen import *

from naps import SimPlatform, verify_stream_output_contract, do_nothing, SimSocPlatform
from naps.cores.debug.packet_console import ConsolePacketSource, ConsolePacketSink


class PacketConsoleTest(unittest.TestCase):
    def check_roundtrip_complex(self, test_packet):
        platform = SimSocPlatform(SimPlatform())

        m = Module()

        source = m.submodules.source = ConsolePacketSource()
        sink = m.submodules.sink = ConsolePacketSink(source.output)

        read = Signal()
        read_ = Signal()
        m.d.comb += read_.eq(read)
        write = Signal()
        write_ = Signal()
        m.d.comb += write_.eq(write)

        def driver(design):

            design.source.write_packet(test_packet)
            yield from do_nothing(20)
            design.source.write_packet(test_packet)
            yield from do_nothing(20)
            self.assertEqual(test_packet, design.sink.read_packet())
            yield from do_nothing(20)
            self.assertEqual(test_packet, design.sink.read_packet())
        platform.add_driver(driver)

        platform.add_sim_clock("sync", 100e6)
        platform.sim(m)

    def test_roundtrip_complex(self):
        self.check_roundtrip_complex(test_packet=[10, 20, 30, 40, 0])

    def test_roundtrip_one_byte(self):
        self.check_roundtrip_complex(test_packet=[0x42])

    def test_source_output_stream_contract(self):
        dut = ConsolePacketSource()
        verify_stream_output_contract(dut)
