from nmigen import *
import unittest

from nmigen.sim import Passive

from lib.bus.stream.sim_util import write_to_stream
from lib.video.image_stream import ImageStream
from lib.video.test_util import write_frame_to_stream, read_frame_from_stream
from lib.video.video_transformer import ImageProxy, VideoTransformer
from util.sim import SimPlatform


class ImageProxyTest(unittest.TestCase):
    def test_request(self):
        x = Signal(16)
        y = Signal(16)
        image = ImageProxy(12, x, y)
        px = image[x + 1, y + 1]
        self.assertIsInstance(px, Signal)
        self.assertEqual(image.offset_mapping, {(1, 1): px})

    def test_request_zero(self):
        x = Signal(16)
        y = Signal(16)
        image = ImageProxy(12, x, y)
        px = image[x, y]
        self.assertIsInstance(px, Signal)
        self.assertEqual(image.offset_mapping, {(0, 0): px})

    def test_request_neg(self):
        x = Signal(16)
        y = Signal(16)
        image = ImageProxy(12, x, y)
        px = image[x - 1, y - 1]
        self.assertIsInstance(px, Signal)
        self.assertEqual(image.offset_mapping, {(-1, -1): px})

    def test_request_equal(self):
        x = Signal(16)
        y = Signal(16)
        image = ImageProxy(12, x, y)
        self.assertIs(image[x + 1, y + 1], image[x + 1, y + 1])
        self.assertIsNot(image[x + 1, y + 2], image[x + 1, y + 1])

    def test_illegal_expr(self):
        x = Signal(16)
        y = Signal(16)
        image = ImageProxy(12, x, y)

        with self.assertRaises(ValueError):
            px = image[0, 0]
        with self.assertRaises(ValueError):
            px = image[x * 2, y * 2]
        with self.assertRaises(ValueError):
            px = image[y, x]


class VideoTransformerTest(unittest.TestCase):
    def check_move_transformer(self, transform_xy, testdata, testdata_transformed):
        m = Module()
        tx, ty = transform_xy

        def transformer_function(x, y, image):
            return image[x + tx, y + ty]

        input = ImageStream(32)
        transformer = m.submodules.transformer = VideoTransformer(input, transformer_function, 10, 10)

        def write_process():
            yield from write_frame_to_stream(input, testdata)
            yield Passive()
            while True:
                yield from write_to_stream(input, line_last=0, frame_last=0, payload=0)

        def read_process():
            frame = (yield from read_frame_from_stream(transformer.output))
            self.assertEqual(frame, testdata_transformed)

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.add_process(write_process, "sync")
        platform.sim(m, read_process)

    def test_passthrough_transformer(self):
        testdata = [[x * y for x in range(10)] for y in range(10)]
        self.check_move_transformer((0, 0), testdata, testdata)


    def test_shift_1x_negative_transformer(self):
        testdata = [[x * y for x in range(10)] for y in range(10)]
        self.check_move_transformer(
            (-1, 0),
            testdata,
            [[0] + [px for px in line[:-1]] for line in testdata]
        )

    def test_shift_1y_negative_transformer(self):
        testdata = [[x * y for x in range(10)] for y in range(10)]
        self.check_move_transformer(
            (0, -1),
            testdata,
            [[0] * 10] + [[px for px in line] for line in testdata[:-1]]
        )

    def test_shift_1x_positive_transformer(self):
        testdata = [[x * y for x in range(10)] for y in range(10)]
        self.check_move_transformer(
            (+1, 0),
            testdata,
            [[px for px in line[1:]] + [0] for line in testdata]
        )

    def test_shift_1y_positive_transformer(self):
        testdata = [[x * y for x in range(10)] for y in range(10)]
        self.check_move_transformer(
            (0, +1),
            testdata,
            [[px for px in line] for line in testdata[1:] + [[0] * 10]]
        )