import unittest

from nmigen import *
from nmigen.sim import Passive

from naps import verify_stream_output_contract, TristateIo, SimPlatform, write_packet_to_stream, read_packet_from_stream
from naps.cores.mipi.d_phy_lane import DPhyDataLane


class DPhyDataLaneTest(unittest.TestCase):
    def test_lp_link(self):
        # in this test, we connect two DPhy lanes together and test if they can talk to each other by
        # sending packets in alternating directions.

        platform = SimPlatform()
        m = Module()

        a = m.submodules.a = DPhyDataLane(TristateIo(2), TristateIo(2), "ddr", initial_driving=True)
        b = m.submodules.b = DPhyDataLane(TristateIo(2), TristateIo(2), "ddr", initial_driving=False)

        with m.If(a.lp_pins.oe):
            m.d.comb += b.lp_pins.i.eq(a.lp_pins.o)
        with m.If(b.lp_pins.oe):
            m.d.comb += a.lp_pins.i.eq(b.lp_pins.o)

        packets = [
            [1, 37, 254]
        ]

        def writer():
            for packet in packets:
                yield from write_packet_to_stream(a.control_input, packet)
                yield from write_packet_to_stream(b.control_input, packet)
            yield Passive()
            while True:
                yield
        platform.add_process(writer, "sync")

        def reader():
            for packet in packets:
                print("b", (yield from read_packet_from_stream(b.control_output)))
                print("a", (yield from read_packet_from_stream(a.control_output)))
        platform.add_process(reader, "sync")

        platform.add_sim_clock("sync", 30e6)
        platform.sim(m)

    def test_stream_contract_control_rx(self):
        m = DPhyDataLane(TristateIo(2), TristateIo(2), "ddr")
        verify_stream_output_contract(m, m.control_input)
