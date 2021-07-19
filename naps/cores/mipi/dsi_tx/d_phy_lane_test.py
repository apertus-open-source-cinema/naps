import unittest

from nmigen import *
from nmigen.sim import Passive

from naps import TristateIo, SimPlatform, write_packet_to_stream, read_packet_from_stream, TristateDdrIo, SimDdr, do_nothing
from .d_phy_lane import DPhyDataLane


class DPhyDataLaneTest(unittest.TestCase):
    def test_lp_link(self):
        # in this test, we connect two DPhy lanes together and test if they can talk to each other by
        # sending packets in alternating directions.

        platform = SimPlatform()
        m = Module()

        a = m.submodules.a = DPhyDataLane(TristateIo(2), TristateDdrIo(2), initial_driving=True, can_lp=True)
        b = m.submodules.b = DPhyDataLane(TristateIo(2), TristateDdrIo(2), initial_driving=False, can_lp=True)

        with m.If(a.lp_pins.oe):
            m.d.comb += b.lp_pins.i.eq(a.lp_pins.o)
        with m.If(b.lp_pins.oe):
            m.d.comb += a.lp_pins.i.eq(b.lp_pins.o)

        packets = [
            [1, 37, 254],
            [1, 37, 254],
        ]

        def writer():
            for packet in packets:
                yield from write_packet_to_stream(a.control_input, packet, timeout=400)
                yield from write_packet_to_stream(a.control_input, [0x0], timeout=400)
                yield from write_packet_to_stream(b.control_input, packet, timeout=400)
                yield from write_packet_to_stream(b.control_input, [0x0], timeout=400)
            yield Passive()
            while True:
                yield
        platform.add_process(writer, "sync")

        def reader():
            for packet in packets:
                self.assertEqual(packet, (yield from read_packet_from_stream(b.control_output, timeout=400)))
                self.assertEqual(packet, (yield from read_packet_from_stream(a.control_output, timeout=400)))
        platform.add_process(reader, "sync")

        platform.add_sim_clock("sync", 30e6)
        platform.sim(m)


    def test_hs_link(self):
        platform = SimPlatform()
        m = Module()

        dut = m.submodules.dut = DPhyDataLane(TristateIo(2), TristateDdrIo(2), initial_driving=True, ddr_domain="hs")
        ddr = m.submodules.ddr = SimDdr(dut.hs_pins, domain="ddr")

        packets = [
            [0x13, 0x00]
        ]

        def writer():
            for packet in packets:
                yield from write_packet_to_stream(dut.hs_input, packet, timeout=400)
                yield from do_nothing(400)
        platform.add_process(writer, "sync")

        # TODO: actual testing

        platform.add_sim_clock("sync", 30e6)
        platform.add_sim_clock("hs", 15e6)
        platform.add_sim_clock("ddr", 30e6)
        platform.sim(m)