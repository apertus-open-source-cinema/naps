import unittest

from lib.bus.stream.sim_util import write_packet_to_stream
from lib.bus.stream.stream import PacketizedStream
from lib.video.adapters import PacketizedStream2ImageStream
from lib.video.test_util import read_frame_from_stream
from util.sim import SimPlatform


class AdaptersTest(unittest.TestCase):
    def test_basic(self):
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
