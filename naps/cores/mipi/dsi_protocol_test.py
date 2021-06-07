import unittest
from nmigen import *
from naps import SimPlatform, SolidColorDemoVideoSource, read_packet_from_stream
from naps.cores.mipi.dsi_protocol import ImageStream2MipiDsiVideoBurstMode


class TestDsiProtocol(unittest.TestCase):
    def test_2_lane(self):
        platform = SimPlatform()
        m = Module()

        source = m.submodules.source = SolidColorDemoVideoSource(480, 480, r=255, g=255, b=0)
        dsi_protocol = m.submodules.dsi_protocol = ImageStream2MipiDsiVideoBurstMode(source.output, num_lanes=2, image_width=480)

        def testbench():
            for i in range(500):
                print((yield from read_packet_from_stream(dsi_protocol.output, timeout=10000000)))

        platform.add_sim_clock("sync", 100e6)
        platform.sim(m, testbench)