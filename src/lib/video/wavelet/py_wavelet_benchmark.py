import sys
from bz2 import BZ2File
from collections import defaultdict
from itertools import product, chain
from multiprocessing import Pool
from pathlib import Path
from pickle import dump

import numpy as np
import rawpy
from PIL import Image
from tqdm import tqdm

from lib.video.wavelet.dng import read_dng, write_dng
from lib.video.wavelet.py_compressor import compress, uncompress, empty_symbol_frequencies_dict, NumericRange, to_chunks, rle_compress_chunks, compute_symbol_frequencies, huffman_encode, \
    generate_huffman_tables, merge_symbol_frequencies
from lib.video.wavelet.py_wavelet import compute_psnr, inverse_multi_stage_wavelet2d, multi_stage_wavelet2d, ty
from util.plot_util import plt_image, plt_show

levels = 3
bit_depth = None


def interleave_v(images):
    first = images[0]
    h, w = first.shape
    n_images = len(images)
    result = np.empty((h * n_images, w), dtype=first.dtype)
    for i, image in enumerate(images):
        result[i::n_images, :] = image
    return result


def load_image(path):
    images = {}
    filename = Path(f).stem

    red, green1, green2, blue, order, estimated_bit_depth = read_dng(f)

    images[f'{filename}--R'] = red
    images[f'{filename}--G1'] = green1
    images[f'{filename}--G2'] = green2
    images[f'{filename}--B'] = blue

    # images with different bit depths cant be combined in one run
    global bit_depth
    assert bit_depth is None or bit_depth == estimated_bit_depth
    bit_depth = estimated_bit_depth

    return images, {(f'{filename}--R', f'{filename}--G1', f'{filename}--G2', f'{filename}--B'): order}


def each_transform_rle(params):
    (filename, image), quantization, input_range = params
    transformed = multi_stage_wavelet2d(image, levels, quantization=quantization)

    chunks = list(to_chunks(transformed, levels))
    region_codes, uncompressed_chunks = zip(*chunks)
    rle_chunks = list(rle_compress_chunks(chunks, levels, input_range))

    symbol_frequencies = compute_symbol_frequencies(region_codes, rle_chunks, levels, input_range)

    roundtripped = inverse_multi_stage_wavelet2d(transformed, levels)
    psnr = compute_psnr(image[16:-16, 16:-16], roundtripped[16:-16, 16:-16], bit_depth=bit_depth)

    return filename, psnr, region_codes, rle_chunks, symbol_frequencies, image, roundtripped


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'usage:\n{sys.argv[0]} input...')
        exit(1)
    _, *files = sys.argv

    images = {}
    metadata = {}
    for f in files:
        new_images, new_metadata = load_image(f)
        images.update(new_images)
        metadata.update(new_metadata)

    input_range = NumericRange(0, 2 ** bit_depth - 1)
    pool = Pool()

    a, b, c, = 48, 32, 16
    d = 4
    quantization = [
        [1, a, a, a * 1.5],
        [1, b, b, b * 1.5],
        [d, c, c, c * 1.5],
    ]

    todo = zip(images.items(), [quantization] * len(images), [input_range] * len(images))
    filenames, psnrs, region_codes_array, rle_chunks_array, symbol_frequencies_array, original, roundtripped = zip(*pool.imap(each_transform_rle, todo))

    for (filename_r, filename_g1, filename_g2, filename_b), order in metadata.items():
        write_dng(
            filename=f'{filename_r.split("--")[0]}-roundtripped',
            red=roundtripped[filenames.index(filename_r)],
            green1=roundtripped[filenames.index(filename_g1)],
            green2=roundtripped[filenames.index(filename_g2)],
            blue=roundtripped[filenames.index(filename_b)],
            bit_depth=bit_depth,
            order=order,
        )

        write_dng(
            filename=f'{filename_r.split("--")[0]}-original',
            red=original[filenames.index(filename_r)],
            green1=original[filenames.index(filename_g1)],
            green2=original[filenames.index(filename_g2)],
            blue=original[filenames.index(filename_b)],
            bit_depth=bit_depth,
            order=order,
        )

    huffman_tables = generate_huffman_tables(merge_symbol_frequencies(symbol_frequencies_array), levels, input_range)

    for region_codes, rle_chunks, (filename, image), psnr in zip(region_codes_array, rle_chunks_array, images.items(), psnrs):
        huffman_encoded = huffman_encode(huffman_tables, region_codes, rle_chunks)
        print(f'{filename: <30}\t1:{(image.size * bit_depth) / len(huffman_encoded):02f}\t{psnr:02f} dB')
