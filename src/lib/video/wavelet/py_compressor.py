from collections import defaultdict

import numpy as np
from numba import jit
from tqdm import tqdm

from lib.video.wavelet.py_wavelet_repack import pack
from util.plot_util import plt_hist, plt_show


def zero_rle(array, codebook):
    codebook = {**codebook, 1: 0}
    keys = sorted(codebook.keys(), reverse=True)
    return list(zero_rle_inner(array, np.array(keys, dtype=np.int32), np.array([codebook[x] for x in keys], dtype=np.int32)))


@jit(nopython=True)
def zero_rle_inner(array, keys, values):
    collected = 0
    for v in array:
        if v == 0:
            collected += 1
        elif collected != 0:
            while collected != 0:
                for i, k in enumerate(keys):
                    if k <= collected:
                        yield values[i]
                        collected -= k
            yield v
        else:
            yield v
    while collected != 0:
        for i, k in enumerate(keys):
            if k <= collected:
                yield values[i]
                collected -= k


def fill_reference_frame(h, w, levels=3):
    ref = np.full((h, w), -1)
    ref[:h // 2, :w // 2] = 1 if levels == 1 else fill_reference_frame(h // 2, w // 2, levels - 1)
    ref[:h // 2, w // 2:] = levels * 10 + 1
    ref[h // 2:, :w // 2] = levels * 10 + 1
    ref[h // 2:, w // 2:] = levels * 10 + 3
    return ref


def min_max_from_region_code(region_code, levels, bit_depth):
    def lf_max(level):
        return (2 ** bit_depth - 1) * (4 ** level)

    l = levels - region_code // 10
    if region_code == 1:
        return 0, lf_max(levels)
    elif region_code % 10 == 1:
        return -lf_max(l) / 2 * 1.25, lf_max(l) / 2 * 1.25
    elif region_code % 10 == 3:
        return -lf_max(l) * 1.25 * 1.25, lf_max(l) * 1.25 * 1.25


def compress_region(data, region_code, levels, bit_depth):
    min_val, max_val = min_max_from_region_code(region_code, levels, bit_depth)
    outliers = data[np.where((data < min_val) | (data > max_val))]
    if len(outliers) > 0:
        raise ValueError
    if region_code == 1:  # we are lf data that shouldnt be rle / huffman encoded
        return data, region_code, (min_val, max_val)
    else:
        codebook = [2, 4, 8, 16, 32, 64]
        return np.array(list(zero_rle(data, {v: i + max_val for i, v in enumerate(codebook)}))), region_code, (min_val, max_val)


def compress(image, levels, bit_depth):
    reference = fill_reference_frame(*image.shape, levels)
    packed_reference = pack(reference, levels)
    packed_image = pack(image, levels)
    result = []
    for ref_line, real_line in list(zip(packed_reference, packed_image)):
        regions = np.unique(ref_line)
        for region in regions:
            if region == 0:
                continue
            result.append(compress_region(real_line[np.where(ref_line == region)], region, levels, bit_depth))

    by_regions = defaultdict(list)
    for data, region, (min_val, max_val) in result:
        by_regions[region].append(data)

    for k, v in by_regions.items():
        all_arr = np.concatenate(v).ravel()
        plt_hist(str(k), all_arr, bins=200)
    plt_show()
