import unittest
from os.path import join, dirname

from nmigen import *
from nmigen.sim import Passive

from lib.bus.stream.sim_util import write_to_stream
from lib.video.image_stream import ImageStream
from lib.video.test_util import write_frame_to_stream, read_frame_from_stream
from lib.video.wavelet import Wavelet2D
from util.sim import SimPlatform
import imageio
import numpy as np


class WaveletTest(unittest.TestCase):
    def test_manual(self):
        platform = SimPlatform()
        m = Module()

        input = ImageStream(8)
        transformer = m.submodules.transformer = Wavelet2D(input, 100, 128)
        image = imageio.imread(join(dirname(__file__), "che.png"))

        def write_process():
            yield from write_frame_to_stream(input, image, pause=False)
            yield Passive()
            while True:
                yield from write_to_stream(input, line_last=0, frame_last=0, payload=0)

        def read_process():
            image = (yield from read_frame_from_stream(transformer.output, timeout=1000, pause=False))
            target_image = np.copy(image)
            for y, row in enumerate(image):
                for x, px in enumerate(row):
                    target_image[y // 2 + ((y % 2) * len(image) // 2)][x // 2 + ((x % 2) * len(row) // 2)] = px
            imageio.imsave(platform.output_filename_base + "_first_level.png", target_image)
            print(np.histogram(np.array(target_image).flatten(), bins=256))

        platform.add_sim_clock("sync", 100e6)
        platform.add_process(write_process, "sync")
        platform.sim(m, read_process)
