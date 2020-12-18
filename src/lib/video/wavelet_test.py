import unittest
from os.path import join, dirname

from nmigen import *
from nmigen.sim import Passive

from lib.bus.stream.fifo import BufferedSyncStreamFIFO
from lib.bus.stream.sim_util import write_to_stream
from lib.video.image_stream import ImageStream
from lib.video.splitter import ImageSplitter, ImageCombiner
from lib.video.test_util import write_frame_to_stream, read_frame_from_stream
from lib.video.wavelet import Wavelet2D, MultiStageWavelet2D
from util.sim import SimPlatform
import imageio
import numpy as np


class WaveletTest(unittest.TestCase):
    def test_wavelet_2d(self):
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
        platform.add_process(write_process, "sync")

        def read_process():
            image = (yield from read_frame_from_stream(transformer.output, timeout=1000, pause=False))
            target_image = np.copy(image)
            for y, row in enumerate(image):
                for x, px in enumerate(row):
                    target_image[y // 2 + ((y % 2) * len(image) // 2)][x // 2 + ((x % 2) * len(row) // 2)] = px
            imageio.imsave(platform.output_filename_base + ".png", target_image)
        platform.add_process(read_process, "sync")

        platform.add_sim_clock("sync", 100e6)
        platform.sim(m)

    def test_stream_splitter(self):
        platform = SimPlatform()
        m = Module()

        input = ImageStream(8)
        transformer = m.submodules.transformer = Wavelet2D(input, 100, 128)
        splitter = m.submodules.splitter = ImageSplitter(transformer.output, 100, 128)

        image = imageio.imread(join(dirname(__file__), "che.png"))

        def write_process():
            yield from write_frame_to_stream(input, image, pause=False)
            yield Passive()
            yield from write_frame_to_stream(input, image, pause=False)
            while True:
                yield from write_to_stream(input, line_last=0, frame_last=0, payload=0)
        platform.add_process(write_process, "sync")

        for i, stream in enumerate(splitter.outputs):
            def gen_read_process():
                i_captured = i
                stream_captured = stream
                def read_process():
                    image = (yield from read_frame_from_stream(stream_captured, timeout=1000, pause=False))
                    imageio.imsave(platform.output_filename_base + "_output_{}.png".format(i_captured), image)
                return read_process
            platform.add_process(gen_read_process(), "sync")

        platform.add_sim_clock("sync", 100e6)
        platform.sim(m)

    def check_multistage(self, n):
        platform = SimPlatform()
        m = Module()

        image = imageio.imread(join(dirname(__file__), "che.png"))
        width = 100
        height = 128

        input = ImageStream(8)
        wavelet = m.submodules.wavelet = MultiStageWavelet2D(input, width, height, stages=n)

        def write_process():
            yield from write_frame_to_stream(input, image, pause=False, timeout=10000)
            yield Passive()
            while True:
                yield from write_frame_to_stream(input, image, pause=False, timeout=10000)
        platform.add_process(write_process, "sync")

        def read_process():
            image = (yield from read_frame_from_stream(wavelet.output, timeout=1000, pause=False))
            imageio.imsave(platform.output_filename_base + ".png", image)
        platform.add_process(read_process, "sync")

        platform.add_sim_clock("sync", 100e6)
        platform.sim(m)

    def test_multistage_1(self):
        self.check_multistage(1)

    def test_multistage_2(self):
        self.check_multistage(2)
