import rawpy
import numpy as np
from pidng.core import RAW2DNG, DNGTags, Tag
from .py_wavelet import ty

positions = [(0, 0), (0, 1), (1, 0), (1, 1)]


def read_dng(filename):
    image = rawpy.imread(filename)
    raw_image = np.array(image.raw_image, dtype=ty)
    arrays = [raw_image[y::2, x::2] for x, y in positions]
    color_desc = image.color_desc.decode("utf-8")
    g = 1
    colors = {}
    for i, (x, y) in enumerate(positions):
        c = color_desc[image.raw_color(x, y)]
        if c == "G":
            c += str(g)
            g += 1
        colors[c] = arrays[i]

    estimated_bit_depth = 12 if np.max(raw_image) > 255 else 8
    return colors['R'], colors['G1'], colors['G2'], colors['B'], list(colors.keys()), estimated_bit_depth


def write_dng(filename, red, green1, green2, blue, bit_depth, order=('G1', 'R', 'B', 'G2')):
    h, w = red.shape
    result = np.empty((h * 2, w * 2), dtype=np.uint16)

    colors = {'R': red, 'G1': green1, 'G2': green2, 'B': blue}
    for (x, y), color in zip(positions, order):
        result[y::2, x::2] = colors[color]

    # set DNG tags.
    t = DNGTags()

    t.set(Tag.ImageWidth, w * 2)
    t.set(Tag.ImageLength, h * 2)
    t.set(Tag.TileWidth, w * 2)
    t.set(Tag.TileLength, h * 2)
    t.set(Tag.PhotometricInterpretation, 32803)
    t.set(Tag.SamplesPerPixel, 1)
    t.set(Tag.BitsPerSample, bit_depth)
    t.set(Tag.CFARepeatPatternDim, [2, 2])
    t.set(Tag.CFAPattern, [{'R': 0, 'G': 1, 'B': 2}[c[0]] for c in order])
    t.set(Tag.BlackLevel, 0)
    t.set(Tag.WhiteLevel, ((1 << bit_depth) - 1))
    t.set(Tag.CalibrationIlluminant1, 21)
    t.set(Tag.AsShotNeutral, [[1, 1], [1, 1], [1, 1]])
    t.set(Tag.DNGVersion, [1, 4, 0, 0])
    t.set(Tag.DNGBackwardVersion, [1, 2, 0, 0])
    t.set(Tag.Make, "Camera Brand")
    t.set(Tag.Model, "Camera Model")
    t.set(Tag.PreviewColorSpace, 2)

    # save to dng file.
    RAW2DNG().convert(result, tags=t, filename=filename)
    return filename + '.dng'
