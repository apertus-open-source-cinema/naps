import unittest
from naps import PacketizedStream, write_packet_to_stream, SimPlatform
from naps.cores.video import PacketizedStream2ImageStream, read_frame_from_stream


class AdaptersTest(unittest.TestCase):
    def test_PacketizedStream2ImageStream(self):
        platform = SimPlatform()
        input_stream = PacketizedStream(32)
        dut = PacketizedStream2ImageStream(input_stream, width=10)

        def write_process():
            for frame in range(10):
                yield from write_packet_to_stream(input_stream, [0 for _ in range(100)])
        platform.add_process(write_process, "sync")

        def read_process():
            for frame in range(10):
                frame = yield from read_frame_from_stream(dut.output)
                self.assertEquals(len(frame), 10)
                self.assertTrue(all(len(l) == 10 for l in frame))
        platform.add_process(read_process, "sync")

        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut)
