import unittest
from nmigen import *
from naps import SimPlatform, read_packet_from_stream, GradientDemoVideoSource
from .video2dsi import ImageStream2Dsi
from .types import DsiShortPacketDataType, DsiLongPacketDataType


class TestDsiProtocol(unittest.TestCase):
    def test_2_lane(self):
        platform = SimPlatform()
        m = Module()

        source = m.submodules.source = GradientDemoVideoSource(direction_y=False, divider=2, width=10, height=10)
        dsi_protocol = m.submodules.dsi_protocol = ImageStream2Dsi(source.output, num_lanes=2, image_width=10)
        m.d.comb += dsi_protocol.v_dummy_line.eq(10)

        def testbench():
            for i in range(100):
                packet_raw = (yield from read_packet_from_stream(dsi_protocol.output, timeout=1000, allow_pause=False))
                packet = [x for word in packet_raw for x in [word & 0xff, word >> 8]]
                print()
                print(packet)
                while packet:
                    if packet[0] == DsiShortPacketDataType.V_SYNC_START:
                        print("VSYNC")
                        packet = packet[4:]
                        continue
                    elif packet[0] == DsiShortPacketDataType.H_SYNC_START:
                        print("HSYNC")
                        packet = packet[4:]
                        continue
                    elif packet[0] == DsiShortPacketDataType.END_OF_TRANSMISSION_PACKET:
                        print("END OF TRANSMISSON")
                        packet = packet[4:]
                        continue
                    elif packet[0] == DsiLongPacketDataType.PACKED_PIXEL_STREAM_24_BIT_RGB_8_8_8:
                        len_header = packet[1] | (packet[2] << 8)
                        print(f"color line (len {len_header})")
                        packet = packet[len_header + 4 + 2:]
                        continue
                    elif packet[0] == DsiLongPacketDataType.BLANKING_PACKET_NO_DATA:
                        len_header = packet[1] | (packet[2] << 8)
                        print(f"blanking (len {len_header})")
                        packet = packet[len_header + 4 + 2:]
                        continue
                    else:
                        print("unknown packet")
                        break

        platform.add_sim_clock("sync", 100e6)
        platform.sim(m, testbench)