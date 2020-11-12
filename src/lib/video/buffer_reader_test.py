import unittest
from math import ceil

from lib.bus.ring_buffer import RingBufferAddressStorage
from lib.bus.stream.sim_util import read_from_stream
from lib.video.buffer_reader import VideoBufferReaderAddressGenerator
from util.sim import SimPlatform


class TestVideoBufferReaderAddressGenerator(unittest.TestCase):
    def check_video_buffer_reader_address_generator(self, width, height, bits_per_pixel):
        ring_buffer = RingBufferAddressStorage(buffer_size=0x1000000, n=4)

        pixels_per_word = 64 / bits_per_pixel
        dut = VideoBufferReaderAddressGenerator(ring_buffer, bits_per_pixel=bits_per_pixel, width_pixels=width, height_pixels=height, stride_pixels=width)

        def testbench():
            x = 0
            y = 0
            frames = 0
            for i in range(ceil(width / pixels_per_word) * height * 2):
                payload, line_last, frame_last = (yield from read_from_stream(dut.output, extract=("payload", "line_last", "frame_last")))
                x += pixels_per_word
                if line_last:
                    print("width", x)
                    self.assertAlmostEqual(x, ceil(width / pixels_per_word) * pixels_per_word, places=4)
                    x = 0
                    y += 1

                if frame_last:
                    print("height", y)
                    self.assertEqual(y, height)
                    y = 0
                    frames += 1
            self.assertEqual(frames, 2)

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.sim(dut, testbench)

    def test_video_buffer_address_generator_19_10_32(self):
        self.check_video_buffer_reader_address_generator(19, 10, 32)

    def test_video_buffer_address_generator_19_10_16(self):
        self.check_video_buffer_reader_address_generator(19, 10, 16)

    def test_video_buffer_address_generator_19_10_12(self):
        self.check_video_buffer_reader_address_generator(19, 10, 12)

    def test_video_buffer_address_generator_automated(self):
        for width in [3, 7, 10, 12, 17, 23]:
            for bits_per_pixel in [3, 7, 8, 10, 12, 13, 17, 23, 24, 32, 33]:
                print(f"\n\nwidth={width} bits_per_pixel={bits_per_pixel}")
                self.check_video_buffer_reader_address_generator(width, 10, bits_per_pixel)
