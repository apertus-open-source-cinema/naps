import sys
from pathlib import Path

import numpy as np
from pathos.pools import ProcessPool as Pool

from lib.video.wavelet.dng import read_dng, write_dng, debayer
from lib.video.wavelet.py_compressor import NumericRange, to_chunks, rle_compress_chunks, compute_symbol_frequencies, generate_huffman_tables, merge_symbol_frequencies, get_huffman_size
from lib.video.wavelet.py_wavelet import inverse_multi_stage_wavelet2d, multi_stage_wavelet2d, ty
from lib.video.wavelet.vifp import vifp_mscale

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


def get_image(images, filenames, rggb_filenames):
    (filename_r, filename_g1, filename_g2, filename_b) = rggb_filenames
    image_planes = dict(
        red=images[filenames.index(filename_r)],
        green1=images[filenames.index(filename_g1)],
        green2=images[filenames.index(filename_g2)],
        blue=images[filenames.index(filename_b)],
    )
    return image_planes, filename_r.split("--")[0]


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
    quantization = np.array([
        [1, a, a, a * 1.5],
        [1, b, b, b * 1.5],
        [d, c, c, c * 1.5],
    ], dtype=ty)

    def each_transform_rle(img, quantization, input_range):
        filename, image = img
        transformed = multi_stage_wavelet2d(image, levels, quantization=quantization)

        chunks = list(to_chunks(transformed, levels))
        region_codes, uncompressed_chunks = zip(*chunks)
        rle_chunks = list(rle_compress_chunks(chunks, levels, input_range, quantization))

        symbol_frequencies = compute_symbol_frequencies(region_codes, rle_chunks, levels, input_range, quantization)

        roundtripped = inverse_multi_stage_wavelet2d(transformed, levels, quantization=quantization)

        return filename, region_codes, rle_chunks, symbol_frequencies, image, roundtripped
    filenames, region_codes_array, rle_chunks_array, symbol_frequencies_array, original, roundtripped = \
        zip(*pool.imap(each_transform_rle, images.items(), [quantization] * len(images), [input_range] * len(images)))

    huffman_tables = generate_huffman_tables(merge_symbol_frequencies(symbol_frequencies_array), levels, input_range, quantization)

    def each_compute_vifp_ratio(metadata):
        rggb_filenames, order = metadata
        common_args = dict(
            bit_depth=bit_depth,
            order=order,
        )
        original_args, filename = get_image(original, filenames, rggb_filenames)
        roundtripped_args, _ = get_image(roundtripped, filenames, rggb_filenames)
        write_dng(filename=f'{filename}-original', **common_args, **original_args)
        write_dng(filename=f'{filename}-roundtripped', **common_args, **roundtripped_args)
        debayered_original = debayer(**common_args, **original_args, debayer_args=dict(output_bps=16))
        debayered_roundtripped = debayer(**common_args, **roundtripped_args, debayer_args=dict(output_bps=16))
        vifp = vifp_mscale(debayered_original, debayered_roundtripped)

        compressed_sizes = []
        for f in rggb_filenames:
            index = filenames.index(f)
            region_codes, rle_chunks, image = region_codes_array[index], rle_chunks_array[index], original[index]
            huffman_encoded_size = get_huffman_size(huffman_tables, region_codes, rle_chunks, levels, input_range, quantization)
            compressed_sizes.append((image.size * bit_depth) / huffman_encoded_size)

        print(f'{filename: <30}\t1:{np.mean(compressed_sizes):02f}\tvif: {vifp:02f}')
    list(map(each_compute_vifp_ratio, metadata.items()))

