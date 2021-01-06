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


def fill_reference_frame(h, w, levels=3):
    ref = np.full((h, w), -1)
    ref[:h // 2, :w // 2] = 1 if levels == 1 else fill_reference_frame(h // 2, w // 2, levels - 1)
    ref[:h // 2, w // 2:] = levels * 10 + 1
    ref[h // 2:, :w // 2] = levels * 10 + 1
    ref[h // 2:, w // 2:] = levels * 10 + 3
    return ref


def min_max_from_region_code(region_code, levels, bit_depth):
    def lf_max(level):
        return (2 ** bit_depth - 1) * (4 ** level) * 2

    level = levels - region_code // 10
    if region_code == 1:
        return 0, lf_max(levels)
    elif region_code % 10 == 1:
        return int(np.floor(-lf_max(level) / 2 * 1.25)), int(np.ceil(lf_max(level) / 2 * 1.25))
    elif region_code % 10 == 3:
        return int(np.floor(-lf_max(level) * 1.25 * 1.25)), int(np.ceil(lf_max(level) * 1.25 * 1.25))


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
        outliers = np.where((result < min_val) | (result > max_val))
        return result


def rle_region_decode(data, region_code, levels, bit_depth, length):
    min_val, max_val = min_max_from_region_code(region_code, levels, bit_depth)
    max_val += len(gen_rle_dict(region_code, levels, bit_depth))
    outliers, = np.where((data < min_val) | (data > max_val))
    read_length = length
    if len(outliers) > 0:
        read_length = np.min(outliers)
    assert read_length > 0
    if region_code == 1:
        return data, length
    else:
        return zero_rle_decode(data[:read_length], gen_rle_dict(region_code, levels, bit_depth), length)


def compress(image, levels, bit_depth):
    reference = fill_reference_frame(*image.shape, levels)
    packed_reference = pack(reference, levels)
    packed_image = pack(image, levels)

    reference_result = []
    non_compressed_result = []
    rle_result = []
    region_codes = []
    for ref_line, real_line in list(zip(packed_reference, packed_image)):
        regions = np.unique(ref_line)
        for region_code in regions:
            if region_code == 0:
                continue
            non_compressed_result.append(real_line[np.where(ref_line == region_code)])
            rle_result.append(rle_region(real_line[np.where(ref_line == region_code)], region_code, levels, bit_depth))
            reference_result.append(ref_line[np.where(ref_line == region_code)])
            region_codes.append(region_code)
    reference = np.concatenate(reference_result).ravel()
    non_compressed = np.concatenate(non_compressed_result).ravel()
    rle_compressed = np.concatenate(rle_result).ravel()

    # statistics to be used for huffman table conversion
    regions, inverse_regions = np.unique(region_codes, return_inverse=True)
    min_max = [min_max_from_region_code(rc, levels, bit_depth) for rc in regions]
    min_max_with_rle = [(min_val, max_val + len(gen_rle_dict(rc, levels, bit_depth))) for (min_val, max_val), rc in zip(min_max, regions)]
    symbol_frequencies = {rc: np.zeros(max_val - min_val + 1) for (min_val, max_val), rc in zip(min_max_with_rle, regions)}
    for rle_chunk, rc, inverse_region in zip(rle_result, region_codes, inverse_regions):
        min_val, max_val = min_max_with_rle[inverse_region]
        symbol_frequencies[rc] += np.bincount(rle_chunk - min_val, minlength=(max_val - min_val + 1))

    assert sum(np.sum(v) for v in symbol_frequencies.values()) == rle_compressed.size

    print(len(non_compressed) / len(rle_compressed))

    decompressed_frame = pack(fill_reference_frame(*image.shape, levels), levels)
    rle_decompressed_frame = pack(fill_reference_frame(*image.shape, levels), levels)
    non_compressed_ptr = 0
    rle_compressed_ptr = 0
    chunk_ptr = 0
    for ref_line, real_line, real_line_rle in list(zip(packed_reference, decompressed_frame, rle_decompressed_frame)):
        regions = np.unique(ref_line)
        for region_code in regions:
            if region_code == 0:
                continue
            region_range, = np.where(ref_line == region_code)
            start, end = np.min(region_range), np.max(region_range) + 1
            region_len = end - start

            non_compressed_slice = non_compressed[non_compressed_ptr:non_compressed_ptr + region_len]
            min_val, max_val = min_max_from_region_code(region_code, levels, bit_depth)
            outliers, = np.where((non_compressed_slice < min_val) | (non_compressed_slice > max_val))
            assert len(outliers) == 0
            real_line[start:end] = non_compressed_slice
            non_compressed_ptr += region_len

            rle_chunk = rle_result[chunk_ptr]
            rle_slice = rle_compressed[rle_compressed_ptr:rle_compressed_ptr + region_len]
            rle_decoded, consumed = rle_region_decode(rle_slice, region_code, levels, bit_depth, region_len)
            assert np.all(rle_slice[0:consumed] == rle_chunk)
            real_line_rle[start:end] = rle_decoded
            rle_compressed_ptr += consumed
            chunk_ptr += 1

    assert np.all(decompressed_frame == rle_decompressed_frame)
    unpacked = unpack(rle_decompressed_frame, levels)
    assert np.all(image == unpacked)

    return non_compressed
