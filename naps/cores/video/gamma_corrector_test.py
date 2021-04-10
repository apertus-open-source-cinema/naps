import unittest
from os.path import join, dirname
import imageio
from nmigen import *
from nmigen.sim import Passive
from naps import SimPlatform
from naps.stream import write_to_stream
from naps.cores.video import ImageStream, TableGammaCorrector, write_frame_to_stream, read_frame_from_stream


class GammaCorrectorTest(unittest.TestCase):
    def check_output(self, corrector_gen, gamma):
        platform = SimPlatform()
        m = Module()

        input = ImageStream(8)
        transformer = m.submodules.transformer = corrector_gen(input, gamma)
        image = imageio.imread(join(dirname(__file__), "wavelet", "che_32.png"))

        # correct the image ourselves to check the corrector's work
        if gamma != 1:
            bpp = 8
            max_pix = 2**bpp - 1
            lut = list(int(max_pix*((v/max_pix)**gamma)+0.5) for v in range(max_pix+1))
            image_corrected = list(list(lut[pixel] for pixel in line) for line in image)
        else: # gamma = 1 should not change image at all
            image_corrected = list(list(pixel for pixel in line) for line in image)

        def write_process():
            yield from write_frame_to_stream(input, image, pause=False)
            yield Passive()

        def read_process():
            result = yield from read_frame_from_stream(transformer.output, timeout=1000, pause=False)
            imageio.imsave(platform.output_filename_base + "_result.png", result)
            self.assertEqual(result, image_corrected)

        platform.add_sim_clock("sync", 100e6)
        platform.add_process(write_process, "sync")
        platform.sim(m, read_process)

    def test_output_table_gamma_corrector_encode(self):
        self.check_output(TableGammaCorrector, 1/2.2)

    def test_output_table_gamma_corrector_decode(self):
        self.check_output(TableGammaCorrector, 2.2)

    def test_output_table_gamma_corrector_nop(self):
        self.check_output(TableGammaCorrector, 1)
