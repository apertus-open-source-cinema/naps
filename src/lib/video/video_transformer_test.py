from nmigen import *
import unittest

from lib.video.video_transformer import ImageProxy


class ImageProxyTest(unittest.TestCase):
    def test_request(self):
        x = Signal(16)
        y = Signal(16)
        image = ImageProxy(12, x, y)
        self.assertIsInstance(image[1, 2], Signal)


class VideoTransforomerTest(unittest.TestCase):
    pass