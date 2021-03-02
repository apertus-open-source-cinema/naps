import unittest
from collections import defaultdict
from os.path import join, dirname
from nmigen import *
from nmigen.sim import Passive
from naps import write_to_stream, ImageStream, write_frame_to_stream, read_frame_from_stream, ImageSplitter, SimPlatform
from .wavelet import Wavelet2D, MultiStageWavelet2D
import imageio
import numpy as np


class WaveletTest(unittest.TestCase):
    def test_wavelet_2d(self):
        image = imageio.imread(join(dirname(__file__), "che_128.png"))
        h, w = image.shape
        platform = SimPlatform()
        m = Module()

        input = ImageStream(8)
        transformer = m.submodules.transformer = Wavelet2D(input, w, h)

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

        platform.add_sim_clock("sync", 1000e6)
        platform.sim(m)

    def test_stream_splitter(self):
        image = imageio.imread(join(dirname(__file__), "che_128.png"))
        h, w = image.shape
        platform = SimPlatform()
        m = Module()

        input = ImageStream(8)
        transformer = m.submodules.transformer = Wavelet2D(input, w, h)
        splitter = m.submodules.splitter = ImageSplitter(transformer.output, w, h)

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
        image = imageio.imread(join(dirname(__file__), "che_64.png"))
        h, w = image.shape
        platform = SimPlatform()
        m = Module()


        input = ImageStream(8)
        wavelet = m.submodules.wavelet = MultiStageWavelet2D(input, w, h, stages=n)

        def write_process():
            yield from write_frame_to_stream(input, image, pause=False, timeout=10000)
            yield Passive()
            while True:
                yield from write_frame_to_stream(input, image, pause=False, timeout=10000)
        platform.add_process(write_process, "sync")

        fifo_levels = defaultdict(lambda: defaultdict(int))
        def find_maximum_fifo_level():
            def find_max_levels(wavelet, level=1):
                for i, fifo in enumerate(wavelet.fifos):
                    current_level = yield fifo.r_level
                    fifo_levels[level][i] = max(current_level, fifo_levels[level][i])
                if hasattr(wavelet, 'next_stage'):
                    yield from find_max_levels(wavelet.next_stage, level + 1)
            yield Passive()
            while True:
                yield from find_max_levels(wavelet)
                yield
        platform.add_process(find_maximum_fifo_level, "sync")

        def read_process():
            for i in range(2):
                image = (yield from read_frame_from_stream(wavelet.output, timeout=1000, pause=False))
                imageio.imsave(platform.output_filename_base + str(i) + ".png", image)
        platform.add_process(read_process, "sync")

        platform.add_sim_clock("sync", 100e6)
        platform.sim(m)
        print("fifo levels:", list(fifo_levels.items()))

    def test_multistage_1(self):
        self.check_multistage(1)

    def test_multistage_2(self):
        self.check_multistage(2)

    def test_multistage_3(self):
        self.check_multistage(3)
