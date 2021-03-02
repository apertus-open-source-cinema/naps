from nmigen import *
import unittest
from nmigen.sim import Passive
from naps import ImageStream, write_to_stream, write_frame_to_stream, read_frame_from_stream, crop, SimPlatform
from .image_convoluter import ImageProxy, ImageConvoluter


class ImageProxyTest(unittest.TestCase):
    def test_request(self):
        x = Signal(16)
        y = Signal(16)
        image = ImageProxy(12, x, y)
        px = image[x + 1, y + 1]
        self.assertIsInstance(px, Signal)
        self.assertEqual(image.offset_mapping, {(-1, -1): px})

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
        self.assertEqual(image.offset_mapping, {(1, 1): px})

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
    def check_move_transformer(self, transform_xy, testdata, testdata_transformed, crop_top=0, crop_left=0, crop_bottom=0, crop_right=0):
        m = Module()
        tx, ty = transform_xy

        def transformer_function(x, y, image):
            return image[x + tx, y + ty]

        input = ImageStream(32)
        transformer = m.submodules.transformer = ImageConvoluter(input, transformer_function, 10, 10)

        def write_process():
            yield from write_frame_to_stream(input, testdata, pause=True)
            yield Passive()
            while True:
                yield from write_to_stream(input, line_last=0, frame_last=0, payload=0)

        def read_process():
            self.assertEqual(crop((yield from read_frame_from_stream(transformer.output, pause=True)), left=crop_left, right=crop_right, bottom=crop_bottom, top=crop_top),
                             testdata_transformed)

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
            [[px for px in line[:-1]] for line in testdata],
            crop_left=1
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

    def check_non_moving_xy(self, transformer_function, crop_top=0, crop_left=0, crop_bottom=0, crop_right=0):
        m = Module()

        width, height = 9, 9
        input = ImageStream(32)
        transformer = m.submodules.transformer = ImageConvoluter(input, transformer_function, width, height)

        def write_process():
            testdata = [[x * y for x in range(width)] for y in range(height)]
            yield from write_frame_to_stream(input, testdata, pause=True)
            yield from write_frame_to_stream(input, testdata, pause=True)
            yield from write_frame_to_stream(input, testdata, pause=True)
            yield Passive()
            while True:
                yield from write_to_stream(input, line_last=0, frame_last=0, payload=0)

        def read_process():
            (yield from read_frame_from_stream(transformer.output, pause=True))
            first = crop((yield from read_frame_from_stream(transformer.output, pause=True)), left=crop_left, right=crop_right, bottom=crop_bottom, top=crop_top)
            second = crop((yield from read_frame_from_stream(transformer.output, pause=True)), left=crop_left, right=crop_right, bottom=crop_bottom, top=crop_top)
            self.assertEqual(first, second)

        platform = SimPlatform()
        platform.add_sim_clock("sync", 100e6)
        platform.add_process(write_process, "sync")
        platform.sim(m, read_process)

    def test_non_moving_xy_pattern(self):
        def transformer_function(x, y, image):
            return (x % 2 == 0) & (y % 2 == 0)
        self.check_non_moving_xy(transformer_function)

    def test_non_moving_xy_passthrough(self):
        def transformer_function(x, y, image):
            return image[x, y]
        self.check_non_moving_xy(transformer_function)

    def test_non_moving_xy_shift_positive(self):
        def transformer_function(x, y, image):
            return image[x+1, y+2]
        self.check_non_moving_xy(transformer_function, crop_right=1, crop_bottom=2)

    def test_non_moving_xy_shift_negative(self):
        def transformer_function(x, y, image):
            return image[x-2, y-1]
        self.check_non_moving_xy(transformer_function)