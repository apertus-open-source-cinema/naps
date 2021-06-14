import unittest
from nmigen import *
from naps import SimPlatform, read_packet_from_stream, GradientDemoVideoSource, DsiPhy, TristateIo, TristateDdrIo, do_nothing
from .video2dsi import ImageStream2Dsi
from .types import DsiShortPacketDataType, DsiLongPacketDataType


class TestDsiProtocol(unittest.TestCase):
    def test_2_lane(self):
        platform = SimPlatform()
        m = Module()

        source = m.submodules.source = GradientDemoVideoSource(direction_y=False, divider=2, width=10, height=10)
        dsi_protocol = m.submodules.dsi_protocol = ImageStream2Dsi(source.output, num_lanes=2, image_width=10)
        m.d.comb += dsi_protocol.vbp.eq(18)

        def testbench():
            for i in range(3):
                packet_raw = (yield from read_packet_from_stream(dsi_protocol.output, timeout=1000, allow_pause=False, pause_after_word=3))
                rest = [x for word in packet_raw for x in [word & 0xff, word >> 8]]
                print("\n", rest)
                while rest:
                    if short_packet := next((opt for opt in DsiShortPacketDataType if opt.value == rest[0]), None):
                        packet, rest = rest[:4], rest[4:]
                        print(f"{short_packet.name} \t {packet}")
                        continue
                    elif long_packet := next((opt for opt in DsiLongPacketDataType if opt.value == rest[0]), None):
                        len_header = rest[1] | (rest[2] << 8)
                        packet, rest = rest[:len_header + 4 + 2], rest[len_header + 4 + 2:]
                        print(f"{long_packet.name} (len={len_header}) \t {packet}")
                        continue
                    else:
                        raise TypeError(f"unknown packet: {rest}")
        platform.add_sim_clock("sync", 100e6)
        platform.sim(m, testbench)

    def test_full_stack(self):
        platform = SimPlatform()
        m = Module()

        source = m.submodules.source = GradientDemoVideoSource(direction_y=False, divider=2, width=10, height=10)
        dsi_protocol = m.submodules.dsi_protocol = ImageStream2Dsi(source.output, num_lanes=2, image_width=10)
        dsi_phy = m.submodules.dsi_phy = DsiPhy(("mipi", 0), num_lanes=2, ddr_domain="ddr", ck_domain="ddr")
        m.d.comb += dsi_phy.hs_input.connect_upstream(dsi_protocol.output)

        def testbench():
            yield from do_nothing(100000)

        platform.add_sim_clock("sync", 100e6)
        platform.add_sim_clock("ddr", 100e6)
        platform.sim(m, testbench)