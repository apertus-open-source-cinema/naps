import unittest
from os.path import join, dirname
import imageio
from nmigen import *
from nmigen.sim import Passive
from naps import SimPlatform, ImageStream, write_frame_to_stream, read_frame_from_stream, write_to_stream, do_nothing
from naps.cores.video.rearrange import ImageSplitter2


class TestImageSplitter2(unittest.TestCase):
    def test_image(self):
        platform = SimPlatform()
        m = Module()

        input = ImageStream(8)
        transformer = m.submodules.transformer = ImageSplitter2(input, 16, 4, 80)
        image = imageio.imread(join(dirname(__file__), "wavelet/che_64.png"))

        def write_process():
            for i in range(2):
                yield from write_frame_to_stream(input, image, pause=False)
            yield Passive()
            yield from do_nothing(100)
        platform.add_process(write_process, "sync")


        for i in range(4):
            def makefunc(i):
                def read_process():
                    for n in range(2):
                        frame = (yield from read_frame_from_stream(transformer.outputs[i], timeout=1000, pause=False))
                        imageio.imsave(platform.output_filename_base + f"_{i}_{n}.png", frame)
                return read_process
            platform.add_process(makefunc(i), "sync")

        platform.add_sim_clock("sync", 100e6)
        platform.sim(m)
