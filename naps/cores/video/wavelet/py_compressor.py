import copy
from itertools import chain, product
from math import log2

import numpy as np
from bitarray import bitarray
from numba import jit
from .py_wavelet_repack import pack, unpack
from .py_wavelet import ty
from huffman import codebook


def zero_rle(array, codebook):
    codebook = {**codebook, 1: 0}
    keys = np.array(sorted(codebook.keys(), reverse=True), dtype=ty)
    values = np.array([codebook[x] for x in keys], dtype=ty)
    return zero_rle_inner(array, keys, values)


@jit(nopython=True)
def zero_rle_inner(input_array, keys, values):
    output_array = np.zeros_like(input_array)

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


@jit(nopython=True)
def n_combine(input_array, n, first_symbol):
    output_array = np.zeros_like(input_array)
    write_ptr = 0
    in_range_cnt = 0
    symbol = 0
    for i in range(len(input_array)):
        elem = input_array[i]
        if -1 <= elem <= +1:
            symbol += (in_range_cnt * 3) * (elem + 1)
            if in_range_cnt == n - 1:
                output_array[write_ptr] = first_symbol + symbol
                write_ptr += 1
                in_range_cnt = 0
                symbol = 0
            else:
                in_range_cnt += 1
        else:
            for x in range(in_range_cnt + 1):
                output_array[write_ptr] = input_array[i - x]
                write_ptr += 1
            in_range_cnt = 0
            symbol = 0
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
        self.min = int(np.sign(min) * np.ceil(np.abs(min)))
        self.max = int(np.sign(max) * np.ceil(np.abs(max)))

    def __repr__(self):
        return f'NumericRange({self.min}, {self.max})'

    def _compute(self, operation, other):
        if isinstance(other, NumericRange):
            other_list = [other.min, other.max]
        else:
            other_list = [other]
        values = [getattr(float(a), operation)(float(b)) for a, b in product([self.min, self.max], other_list)]
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


def numeric_range_from_region_code(region_code, levels, input_range, quantization):
    lf = lambda nr: nr + nr
    hf = lambda nr: (nr - nr) + (-nr - nr + nr + nr + 4) // 8

    lf_h = lambda level: lf(input_range) if level == 1 else lf(lf_v_quantized(level - 1))
    lf_v = lambda level: lf(lf_h(level))
    lf_v_quantized = lambda level: lf_v(level) / quantization[levels - level - 1][0]
    hf_top_right = lambda level: hf(lf_h(level))
    hf_bottom_left = lambda level: hf(lf_v(level))
    hf_bottom_right = lambda level: hf(hf_top_right(level))

    if region_code == 1:
        return lf_v_quantized(levels)

    level = (levels - region_code // 10) + 1
    if region_code % 10 == 2:
        return hf_top_right(level) / quantization[level - 1][1]
    elif region_code % 10 == 3:
        return hf_bottom_left(level) / quantization[level - 1][2]
    elif region_code % 10 == 4:
        return hf_bottom_right(level) / quantization[level - 1][3]


def numeric_range_from_region_code_with_rle(region_code, levels, input_range, quantization):
    nr = numeric_range_from_region_code(region_code, levels, input_range, quantization)
    return NumericRange(nr.min, nr.max + len(gen_rle_dict(region_code, levels, input_range, quantization)) + (3**2) + (3 ** 3))


def gen_rle_dict(region_code, levels, input_range, quantization):
    rle_codes = [4, 5, 6, 7, 8, 10, 12, 15, 18, 25, 35, 50]
    nr = numeric_range_from_region_code(region_code, levels, input_range, quantization)
    return {v: i + nr.max for i, v in enumerate(rle_codes)}


def rle_region(data, region_code, levels, input_range, quantization):
    nr = numeric_range_from_region_code(region_code, levels, input_range, quantization)
    outliers = data[np.where((data < nr.min) | (data > nr.max))]
    if len(outliers) > 0:
        raise ValueError
    if region_code == 1:
        return data  # don't do rle for lf data
    else:
        rled_region = zero_rle(data, gen_rle_dict(region_code, levels, input_range, quantization))
        highest_rle_symbol = nr.max + len(gen_rle_dict(region_code, levels, input_range, quantization))
        merge_3 = n_combine(rled_region, 3, highest_rle_symbol)
        merge_2 = n_combine(merge_3, 2, highest_rle_symbol + (3 ** 3))
        return merge_2


def rle_region_decode(data, region_code, levels, length, input_range, quantization):
    numeric_range = numeric_range_from_region_code_with_rle(region_code, levels, input_range, quantization)
    outliers, = np.where((data < numeric_range.min) | (data > numeric_range.max))
    read_length = length
    if len(outliers) > 0:
        read_length = np.min(outliers)
    assert read_length > 0
    if region_code == 1:
        return data, length
    else:
        return zero_rle_decode(data[:read_length], gen_rle_dict(region_code, levels, input_range, quantization), length)


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


def rle_compress_chunks(chunks, levels, input_range, quantization):
    for rc, data in chunks:
        yield rle_region(data, rc, levels, input_range, quantization)


def empty_symbol_frequencies_dict(levels, input_range, quantization):
    regions = possible_region_codes(levels)
    numeric_range = [numeric_range_from_region_code_with_rle(rc, levels, input_range, quantization) for rc in regions]
    return {rc: np.zeros(nr.max - nr.min + 1) for nr, rc in zip(numeric_range, regions)}


def compute_symbol_frequencies(region_codes, compressed_chunks, levels, input_range, quantization):
    symbol_frequencies = empty_symbol_frequencies_dict(levels, input_range, quantization)
    for compressed_chunk, rc in zip(compressed_chunks, region_codes):
        nr = numeric_range_from_region_code_with_rle(rc, levels, input_range, quantization)
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


def generate_huffman_tables(symbol_frequencies, levels, input_range, quantization, max_table_size=1024):
    to_return = {}
    for rc, frequencies in symbol_frequencies.items():
        nr = numeric_range_from_region_code_with_rle(rc, levels, input_range, quantization)
        symbols = np.arange(nr.min, nr.max + 1, dtype=ty)
        if rc == 1:
            cb = {}
        else:
            sorting_indecies = np.argsort(frequencies)

            escape_symbol = nr.max + 1
            real_symbols = np.append(symbols[sorting_indecies[-max_table_size:]], [escape_symbol])

            escape_frequency = np.sum(frequencies[:-max_table_size])
            real_frequencies = np.append(frequencies[sorting_indecies[-max_table_size:]], [escape_frequency])

            cb = codebook(zip(real_symbols, real_frequencies))

        to_return[rc] = {k: bitarray(v) for k, v in cb.items()}

    return to_return


def get_huffman_size(huffman_tables, region_codes, rle_chunks, levels, input_range, quantization):
    huffman_length_arrays = {}
    for rc, huffman_table in huffman_tables.items():
        nr = numeric_range_from_region_code_with_rle(rc, levels, input_range, quantization)
        bits_needed = int(np.ceil(log2(nr.max - nr.min + 1)))
        if rc == 1:
            lengths = np.full(nr.max - nr.min + 1, bits_needed, dtype=np.uint64)
        else:
            escape_symbol = nr.max + 1
            escape_symbol_length = len(huffman_table[escape_symbol])
            lengths = np.full(nr.max - nr.min + 1, bits_needed + escape_symbol_length, dtype=np.uint64)
            for symbol, code in huffman_table.items():
                if symbol != escape_symbol:
                    lengths[symbol - nr.min] = len(code)
        huffman_length_arrays[rc] = lengths

    size = 0
    for rc, data in zip(region_codes, rle_chunks):
        nr = numeric_range_from_region_code_with_rle(rc, levels, input_range, quantization)
        size += np.sum(huffman_length_arrays[rc][data - nr.min])
    return size


def huffman_encode(huffman_tables, region_codes, rle_chunks):
    huffman_encoded = bitarray()
    for rc, data in zip(region_codes, rle_chunks):
        huffman_encoded.encode(huffman_tables[rc], data)
    return huffman_encoded


def compress(image, levels, input_range, quantization):
    chunks = list(to_chunks(image, levels))
    region_codes, uncompressed_chunks = zip(*chunks)
    rle_chunks = list(rle_compress_chunks(chunks, levels, input_range, quantization))

    non_compressed = np.concatenate(list(uncompressed_chunks))
    rle_compressed = np.concatenate(list(rle_chunks))
    rle_ratio = len(non_compressed) / len(rle_compressed)

    symbol_frequencies = compute_symbol_frequencies(region_codes, rle_chunks, levels, input_range, quantization)
    huffman_tables = generate_huffman_tables(symbol_frequencies, levels, input_range, quantization)
    huffman_encoded = huffman_encode(huffman_tables, region_codes, rle_chunks)

    huffman_ratio = len(rle_compressed) / len(huffman_encoded.tobytes())
    total_ratio = image.size * (log2(input_range.max + 1) / 8) / len(huffman_encoded.tobytes())

    return rle_compressed, symbol_frequencies, rle_ratio, huffman_ratio, total_ratio


def uncompress(original_shape, compressed, levels, bit_depth, quantization):
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
            rle_decoded, consumed = rle_region_decode(rle_slice, region_code, levels, bit_depth, region_len, quantization)
            line[start:end] = rle_decoded
            rle_compressed_ptr += consumed

    return unpack(rle_decompressed_frame, levels)
