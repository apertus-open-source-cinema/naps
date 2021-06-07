import unittest
from nmigen import *
from naps import SimPlatform, SolidColorDemoVideoSource, read_packet_from_stream
from naps.cores.mipi.dsi_protocol import ImageStream2MipiDsiVideoBurstMode
from naps.cores.mipi.py_dsi_generator import ShortPacketDataType, LongPacketDataType
from naps.cores.video.demo_source import GradientDemoVideoSource


class TestDsiProtocol(unittest.TestCase):
    def test_2_lane(self):
        platform = SimPlatform()
        m = Module()

        source = m.submodules.source = GradientDemoVideoSource(direction_y=False, divider=2, width=10, height=10)
        dsi_protocol = m.submodules.dsi_protocol = ImageStream2MipiDsiVideoBurstMode(source.output, num_lanes=2, image_width=10)
        m.d.comb += dsi_protocol.v_dummy_line.eq(10)

        def testbench():
            for i in range(100):
                packet_raw = (yield from read_packet_from_stream(dsi_protocol.output, timeout=1000, allow_pause=False))
                packet = [x for word in packet_raw for x in [word & 0xff, word >> 8]]
                print()
                print(packet)
                while packet:
                    if packet[0] == ShortPacketDataType.V_SYNC_START:
                        print("VSYNC")
                        packet = packet[4:]
                        continue
                    elif packet[0] == ShortPacketDataType.H_SYNC_START:
                        print("HSYNC")
                        packet = packet[4:]
                        continue
                    elif packet[0] == ShortPacketDataType.END_OF_TRANSMISSION_PACKET:
                        print("END OF TRANSMISSON")
                        packet = packet[4:]
                        continue
                    elif packet[0] == LongPacketDataType.PACKED_PIXEL_STREAM_24_BIT_RGB_8_8_8:
                        len_header = packet[1] | (packet[2] << 8)
                        print(f"color line (len {len_header})")
                        packet = packet[len_header + 4 + 2:]
                        continue
                    elif packet[0] == LongPacketDataType.BLANKING_PACKET_NO_DATA:
                        len_header = packet[1] | (packet[2] << 8)
                        print(f"blanking (len {len_header})")
                        packet = packet[len_header + 4 + 2:]
                        continue
                    else:
                        print("unknown packet")
                        break

        platform.add_sim_clock("sync", 100e6)
        platform.sim(m, testbench)