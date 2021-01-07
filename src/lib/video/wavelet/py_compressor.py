from itertools import chain

import numpy as np
from numba import jit

from lib.video.wavelet.py_wavelet_repack import pack, unpack
from util.plot_util import plt_show, plt_image


def zero_rle(array, codebook):
    codebook = {**codebook, 1: 0}
    keys = np.array(sorted(codebook.keys(), reverse=True), dtype=np.int32)
    values = np.array([codebook[x] for x in keys], dtype=np.int32)
    return list(zero_rle_inner(array, keys, values))


@jit(nopython=True)
def zero_rle_inner(array, keys, values):
    zeroes = 0
    for v in array:
        if v == 0:
            zeroes += 1
        elif zeroes != 0:
            while zeroes != 0:
                for i, k in enumerate(keys):
                    if k <= zeroes:
                        yield values[i]
                        zeroes -= k
                        break
            yield v
        else:
            yield v
    while zeroes != 0:
        for i, k in enumerate(keys):
            if k <= zeroes:
                yield values[i]
                zeroes -= k


def zero_rle_decode(array, codebook, length):
    result = np.empty(length, dtype=np.int32)
    # This assumes that the rle symbols are continuous starting with the one with the lowest value
    codebook_start = min(codebook.values())
    codebook_list = np.array(list(codebook.keys()), dtype=np.int32)
    read = zero_rle_decode_inner(array, result, codebook_list, codebook_start)
    if read <= 0:
        assert False
    return result, read


@jit('int32(int32[:], int32[:], int32[:], int32)', nopython=True)
def zero_rle_decode_inner(input_array, output_array, codebook, codebook_start):
    target_write_index = len(output_array)
    write_index = 0
    for i, v in enumerate(input_array):
        # This assumes that the rle symbols are above the range of allowed normal codewords
        if v < codebook_start:
            output_array[write_index] = v
            write_index += 1
        else:
            n_zeros = codebook[v - codebook_start]
            for _ in range(n_zeros):
                output_array[write_index] = 0
                write_index += 1
        if write_index > target_write_index:
            return -42
        if write_index == target_write_index:
            return i + 1
    return -write_index


def possible_region_codes(levels=3):
    return list(chain(*[
        [1],
        *[[l * 10 + 1, l * 10 + 3] for l in range(1, levels + 1)],
    ]))


def fill_reference_frame(h, w, levels=3):
    ref = np.full((h, w), -1)
    ref[:h // 2, :w // 2] = 1 if levels == 1 else fill_reference_frame(h // 2, w // 2, levels - 1)
    ref[:h // 2, w // 2:] = levels * 10 + 1
    ref[h // 2:, :w // 2] = levels * 10 + 1
    ref[h // 2:, w // 2:] = levels * 10 + 3
    return ref


def min_max_from_region_code(region_code, levels, bit_depth):
    def lf_h(level):
        return 2 ** bit_depth - 1 if level == 0 else lf_v(level - 1) * 2
    def lf_v(level):
        return lf_h(level) * 2
    def abs_hf_top_right(level):
        return lf_h(level) * 1.25
    def abs_hf_bottom_left(level):
        return lf_v(level) * 1.25
    def abs_hf_bottom_right(level):
        return abs_hf_top_right(level) * 2.5

    if region_code == 1:
        return 0, lf_v(levels)

    level = (levels - region_code // 10) + 1
    if region_code % 10 == 1:
        return -int(abs_hf_bottom_left(level)), int(np.ceil(abs_hf_bottom_left(level)))
    elif region_code % 10 == 3:
        return -int(abs_hf_top_right(level)), int(np.ceil(abs_hf_bottom_right(level)))


def min_max_from_region_code_with_rle(region_code, levels, bit_depth):
    min_val, max_val = min_max_from_region_code(region_code, levels, bit_depth)
    return min_val, max_val + len(gen_rle_dict(region_code, levels, bit_depth))


def gen_rle_dict(region_code, levels, bit_depth):
    rle_codes = list(range(2, 300))
    min_val, max_val = min_max_from_region_code(region_code, levels, bit_depth)
    return {v: i + max_val for i, v in enumerate(rle_codes)}


def rle_region(data, region_code, levels, bit_depth):
    min_val, max_val = min_max_from_region_code(region_code, levels, bit_depth)
    outliers = data[np.where((data < min_val) | (data > max_val))]
    if len(outliers) > 0:
        raise ValueError
    if region_code == 1:
        return data  # dont to rle for lf data
    else:
        result = np.array(list(zero_rle(data, gen_rle_dict(region_code, levels, bit_depth))), dtype=np.int32)
        return result


def rle_region_decode(data, region_code, levels, bit_depth, length):
    min_val, max_val = min_max_from_region_code_with_rle(region_code, levels, bit_depth)
    outliers, = np.where((data < min_val) | (data > max_val))
    read_length = length
    if len(outliers) > 0:
        read_length = np.min(outliers)
    assert read_length > 0
    if region_code == 1:
        return data, length
    else:
        return zero_rle_decode(data[:read_length], gen_rle_dict(region_code, levels, bit_depth), length)


def to_chunks(image, levels):
    reference = fill_reference_frame(*image.shape, levels)
    packed_reference = pack(reference, levels)
    packed_image = pack(image, levels)

    for ref_line, real_line in list(zip(packed_reference, packed_image)):
        regions = np.unique(ref_line)
        for region_code in regions:
            if region_code == 0:
                continue
            yield region_code, real_line[np.where(ref_line == region_code)]


def compress_chunks(chunks, levels, bit_depth):
    for rc, data in chunks:
        yield rle_region(data, rc, levels, bit_depth)


def empty_symbol_frequencies_dict(levels, bit_depth):
    regions = possible_region_codes(levels)
    min_max = [min_max_from_region_code_with_rle(rc, levels, bit_depth) for rc in regions]
    return {rc: np.zeros(max_val - min_val + 1) for (min_val, max_val), rc in zip(min_max, regions)}


def compute_symbol_frequencies(region_codes, compressed_chunks, levels, bit_depth):
    symbol_frequencies = empty_symbol_frequencies_dict(levels, bit_depth)
    for compressed_chunk, rc in zip(compressed_chunks, region_codes):
        min_val, max_val = min_max_from_region_code_with_rle(rc, levels, bit_depth)
        symbol_frequencies[rc] += np.bincount(compressed_chunk - min_val, minlength=(max_val - min_val + 1))

    assert np.sum(np.concatenate(list(symbol_frequencies.values()))) == np.concatenate(compressed_chunks).size
    return symbol_frequencies


def compress(image, levels, bit_depth):
    chunks = list(to_chunks(image, levels))
    region_codes, uncompressed_chunks = zip(*chunks)
    compressed_chunks = list(compress_chunks(chunks, levels, bit_depth))

    non_compressed = np.concatenate(list(uncompressed_chunks))
    rle_compressed = np.concatenate(list(compressed_chunks))
    rle_ratio = len(non_compressed) / len(rle_compressed)

    symbol_frequencies = compute_symbol_frequencies(region_codes, compressed_chunks, levels, bit_depth)

    return rle_compressed, symbol_frequencies, rle_ratio


def uncompress(original_shape, compressed, levels, bit_depth):
    reference = fill_reference_frame(*original_shape, levels)
    packed_reference = pack(reference, levels)
    rle_decompressed_frame = pack(fill_reference_frame(*original_shape, levels), levels)
    rle_compressed_ptr = 0
    for ref_line, line in list(zip(packed_reference, rle_decompressed_frame)):
        regions = np.unique(ref_line)
        for region_code in regions:
            if region_code == 0:
                continue
            region_range, = np.where(ref_line == region_code)
            start, end = np.min(region_range), np.max(region_range) + 1
            region_len = end - start

            rle_slice = compressed[rle_compressed_ptr:rle_compressed_ptr + region_len]
            rle_decoded, consumed = rle_region_decode(rle_slice, region_code, levels, bit_depth, region_len)
            line[start:end] = rle_decoded
            rle_compressed_ptr += consumed

    return unpack(rle_decompressed_frame, levels)
