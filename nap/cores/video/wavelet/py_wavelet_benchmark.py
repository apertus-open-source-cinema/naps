import marshal, sys, types
from itertools import repeat
from pathlib import Path
import numpy as np
import rawpy
from multiprocessing import Pool

from .dng import read_dng, write_dng
from .py_compressor import NumericRange, to_chunks, rle_compress_chunks, compute_symbol_frequencies, generate_huffman_tables, merge_symbol_frequencies, get_huffman_size
from .py_wavelet import inverse_multi_stage_wavelet2d, multi_stage_wavelet2d, ty
from .vifp import vifp_mscale

levels = 3
bit_depth = None


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


def wrapper(args):
    fun, g, *args = args
    code = marshal.loads(fun)
    fun = types.FunctionType(code, dict(g) | globals(), "fn")
    return fun(*args)


def pmap(fn, *iterables, capture=(), threads=None):
    g = [(k, v) for k, v in globals().items() if k in capture]
    with Pool(threads) as pool:
        return pool.map(wrapper, zip(repeat(marshal.dumps(fn.__code__)), repeat(g), *iterables))


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

    quantization = np.array([
        [1, 48, 48, 72],
        [2, 48, 48, 24],
        [1, 48, 48, 24],
    ], dtype=ty)


    def each_transform_rle(img):
        filename, image = img
        transformed = multi_stage_wavelet2d(image, levels, quantization=quantization)

        chunks = list(to_chunks(transformed, levels))
        region_codes, uncompressed_chunks = zip(*chunks)
        rle_chunks = list(rle_compress_chunks(chunks, levels, input_range, quantization))

        symbol_frequencies = compute_symbol_frequencies(region_codes, rle_chunks, levels, input_range, quantization)

        roundtripped = inverse_multi_stage_wavelet2d(transformed, levels, quantization=quantization)

        return filename, region_codes, rle_chunks, symbol_frequencies, image, roundtripped


    filenames, region_codes_array, rle_chunks_array, symbol_frequencies_array, original, roundtripped = \
        zip(*map(each_transform_rle, images.items()))

    huffman_tables = generate_huffman_tables(merge_symbol_frequencies(symbol_frequencies_array), levels, input_range, quantization)


    def recombine_images(metadata):
        rggb_filenames, order = metadata
        filename = rggb_filenames[0].split("--")[0]

        per_plane = []
        for f in rggb_filenames:
            idx = filenames.index(f)
            per_plane.append((original[idx], roundtripped[idx], region_codes_array[idx], rle_chunks_array[idx]))
        return per_plane, order, filename


    recombined_images = map(recombine_images, metadata.items())


    def each_compute_vifp_ratio(recombined_image):
        (r, g1, g2, b), order, filename = recombined_image
        original_path = write_dng(f'{filename}-original', r[0], g1[0], g2[0], b[0], bit_depth, order)
        debayered_original = rawpy.imread(original_path).postprocess(output_bps=16)
        roundtripped_path = write_dng(f'{filename}-roundtripped', r[1], g1[1], g2[1], b[1], bit_depth, order)
        debayered_roundtripped = rawpy.imread(roundtripped_path).postprocess(output_bps=16)
        vifp = vifp_mscale(debayered_original, debayered_roundtripped)

        compressed_sizes = []
        for plane in (r, g1, g2, b):
            original, roundtripped, region_codes, rle_chunks = plane
            huffman_encoded_size = get_huffman_size(huffman_tables, region_codes, rle_chunks, levels, input_range, quantization)
            compressed_sizes.append((original.size * bit_depth) / huffman_encoded_size)

        print(f'{filename: <30}\t1:{np.mean(compressed_sizes):02f}\tvif: {vifp:02f}')


    list(pmap(each_compute_vifp_ratio, recombined_images, capture=('bit_depth', 'order', 'quantization', 'huffman_tables'), threads=4))
