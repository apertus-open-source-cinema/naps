import copy
from collections import defaultdict
from itertools import chain, product
from math import log2

import numpy as np
from bitarray import bitarray
from numba import jit

from lib.video.wavelet.py_wavelet_repack import pack, unpack
from lib.video.wavelet.py_wavelet import ty
from huffman import codebook

from util.plot_util import plt_hist, plt_show, plt_discrete_hist


@jit(nopython=True)
def bad_entropy_coding(input_array):
    fetchback = 4
    fetchback_div = 2
    value_div = 2
    sub_div = 2
    delay = 1

    output = np.empty_like(input_array)
    integrator_history = np.empty_like(input_array)
    integrator = np.zeros(delay + 1, dtype=ty)
    integrator_ptr = 0
    for i, v in enumerate(input_array):
        delayed_integrator_val = integrator[integrator_ptr + 1 if integrator_ptr < delay else 0]
        output[i] = v - (delayed_integrator_val // sub_div)
        integrator_history[i] = delayed_integrator_val

        integrator[integrator_ptr] = integrator[integrator_ptr - 1 if integrator_ptr > 0 else delay - 1]
        integrator[integrator_ptr] -= v // value_div
        integrator[integrator_ptr] -= np.sign(integrator[integrator_ptr]) * min(np.abs(integrator[integrator_ptr]), fetchback)
        integrator[integrator_ptr] /= fetchback_div

        if integrator_ptr < delay:
            integrator_ptr += 1
        else:
            integrator_ptr = 0

    return output, integrator_history


def zero_rle(array, codebook):
    codebook = {**codebook, 1: 0}
    keys = np.array(sorted(codebook.keys(), reverse=True), dtype=ty)
    values = np.array([codebook[x] for x in keys], dtype=ty)
    output_array = np.zeros_like(array)
    return zero_rle_inner(array, output_array, keys, values)


@jit(nopython=True)
def zero_rle_inner(input_array, output_array, keys, values):
    zeroes = 0
    write_ptr = 0
    for v in input_array:
        if v == 0:
            zeroes += 1
        elif zeroes != 0:
            while zeroes != 0:
                for i, k in enumerate(keys):
                    if k <= zeroes:
                        output_array[write_ptr] = values[i]
                        write_ptr += 1
                        zeroes -= k
                        break
            output_array[write_ptr] = v
            write_ptr += 1
        else:
            output_array[write_ptr] = v
            write_ptr += 1
    while zeroes != 0:
        for i, k in enumerate(keys):
            if k <= zeroes:
                output_array[write_ptr] = values[i]
                write_ptr += 1
                zeroes -= k

    return output_array[:write_ptr]


def zero_rle_decode(array, codebook, length):
    result = np.empty(length, dtype=ty)
    # This assumes that the rle symbols are continuous starting with the one with the lowest value
    codebook_start = min(codebook.values())
    codebook_list = np.array(list(codebook.keys()), dtype=ty)
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
        *[[l * 10 + 2, l * 10 + 3, l * 10 + 4] for l in range(1, levels + 1)],
    ]))


def fill_reference_frame(h, w, levels=3):
    ref = np.zeros((h, w), dtype=ty)
    ref[:h // 2, :w // 2] = 1 if levels == 1 else fill_reference_frame(h // 2, w // 2, levels - 1)
    ref[:h // 2, w // 2:] = levels * 10 + 2
    ref[h // 2:, :w // 2] = levels * 10 + 3
    ref[h // 2:, w // 2:] = levels * 10 + 4
    return ref


class NumericRange:
    def __init__(self, min, max):
        self.min = min
        self.max = max

    def __repr__(self):
        return f'NumericRange({self.min}, {self.max})'

    def _compute(self, operation, other):
        if isinstance(other, NumericRange):
            other_list = [other.min, other.max]
        else:
            other_list = [other]
        values = [getattr(a, operation)(b) for a, b in product([self.min, self.max], other_list)]
        return NumericRange(min(values), max(values))

    def __neg__(self):
        return NumericRange(-self.max, -self.min)

    def __add__(self, other):
        return self._compute('__add__', other)

    def __sub__(self, other):
        return self._compute('__sub__', other)

    def __mul__(self, other):
        return self._compute("__mul__", other)

    def __truediv__(self, other):
        return self._compute("__truediv__", other)

    def __floordiv__(self, other):
        return self._compute("__floordiv__", other)


def numeric_range_from_region_code(region_code, levels, input_range):
    lf = lambda nr: nr + nr
    hf = lambda nr: (nr - nr) + (-nr - nr + nr + nr + 4) // 8

    lf_h = lambda level: input_range if level == 0 else lf(lf_v(level - 1))
    lf_v = lambda level: lf(lf_h(level))
    hf_top_right = lambda level: hf(lf_h(level))
    hf_bottom_left = lambda level: hf(lf_v(level))
    hf_bottom_right = lambda level: hf(hf_top_right(level))

    if region_code == 1:
        return lf_v(levels)

    level = (levels - region_code // 10) + 1
    if region_code % 10 == 2:
        return hf_top_right(level)
    elif region_code % 10 == 3:
        return hf_bottom_left(level)
    elif region_code % 10 == 4:
        return hf_bottom_right(level)


def numeric_range_from_region_code_with_rle(region_code, levels, input_range):
    nr = numeric_range_from_region_code(region_code, levels, input_range)
    return NumericRange(nr.min, nr.max + len(gen_rle_dict(region_code, levels, input_range)))


def gen_rle_dict(region_code, levels, input_range):
    rle_codes = list(range(2, 300))
    nr = numeric_range_from_region_code(region_code, levels, input_range)
    return {v: i + nr.max for i, v in enumerate(rle_codes)}


def rle_region(data, region_code, levels, input_range):
    nr = numeric_range_from_region_code(region_code, levels, input_range)
    outliers = data[np.where((data < nr.min) | (data > nr.max))]
    if len(outliers) > 0:
        raise ValueError
    if region_code == 1:
        return data  # dont to rle for lf data
    else:
        return zero_rle(data, gen_rle_dict(region_code, levels, input_range))


def rle_region_decode(data, region_code, levels, input_range, length):
    numeric_range = numeric_range_from_region_code_with_rle(region_code, levels, input_range)
    outliers, = np.where((data < numeric_range.min) | (data > numeric_range.max))
    read_length = length
    if len(outliers) > 0:
        read_length = np.min(outliers)
    assert read_length > 0
    if region_code == 1:
        return data, length
    else:
        return zero_rle_decode(data[:read_length], gen_rle_dict(region_code, levels, input_range), length)


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


def rle_compress_chunks(chunks, levels, bit_depth):
    for rc, data in chunks:
        yield rle_region(data, rc, levels, bit_depth)


def empty_symbol_frequencies_dict(levels, input_range):
    regions = possible_region_codes(levels)
    numeric_range = [numeric_range_from_region_code_with_rle(rc, levels, input_range) for rc in regions]
    return {rc: np.zeros(nr.max - nr.min + 1) for nr, rc in zip(numeric_range, regions)}


def compute_symbol_frequencies(region_codes, compressed_chunks, levels, input_range):
    symbol_frequencies = empty_symbol_frequencies_dict(levels, input_range)
    for compressed_chunk, rc in zip(compressed_chunks, region_codes):
        nr = numeric_range_from_region_code_with_rle(rc, levels, input_range)
        symbol_frequencies[rc] += np.bincount(compressed_chunk - nr.min, minlength=(nr.max - nr.min + 1))

    assert np.sum(np.concatenate(list(symbol_frequencies.values()))) == np.concatenate(compressed_chunks).size
    return symbol_frequencies


def merge_symbol_frequencies(symbol_frequencies_list):
    head, *rest = symbol_frequencies_list
    result = copy.deepcopy(head)
    for other in rest:
        for k in result.keys():
            result[k] += other[k]
    return result


def generate_huffman_tables(symbol_frequencies, levels, bit_depth):
    to_return = {}
    for rc, frequencies in symbol_frequencies.items():
        nr = numeric_range_from_region_code_with_rle(rc, levels, bit_depth)
        symbols = np.arange(nr.min, nr.max)

        nonzero_indecies = np.where(frequencies != 0)
        real_frequencies = np.append(frequencies[nonzero_indecies], [1])
        real_symbols = np.append(symbols[nonzero_indecies], [symbols[-1] + 1])

        cb = codebook(zip(real_symbols, real_frequencies))
        to_return[rc] = {k: bitarray(v) for k, v in cb.items()}

    return to_return


def huffman_encode(huffman_tables, region_codes, rle_chunks):
    huffman_encoded = bitarray()
    for rc, data in zip(region_codes, rle_chunks):
        huffman_encoded.encode(huffman_tables[rc], data)
    return huffman_encoded


def compress(image, levels, input_range):
    chunks = list(to_chunks(image, levels))
    region_codes, uncompressed_chunks = zip(*chunks)
    rle_chunks = list(rle_compress_chunks(chunks, levels, input_range))

    non_compressed = np.concatenate(list(uncompressed_chunks))
    rle_compressed = np.concatenate(list(rle_chunks))
    rle_ratio = len(non_compressed) / len(rle_compressed)

    symbol_frequencies = compute_symbol_frequencies(region_codes, rle_chunks, levels, input_range)
    huffman_tables = generate_huffman_tables(symbol_frequencies, levels, input_range)
    huffman_encoded = huffman_encode(huffman_tables, region_codes, rle_chunks)

    huffman_ratio = len(rle_compressed) / len(huffman_encoded.tobytes())
    total_ratio = image.size * (log2(input_range.max + 1) / 8) / len(huffman_encoded.tobytes())

    return rle_compressed, symbol_frequencies, rle_ratio, huffman_ratio, total_ratio


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
