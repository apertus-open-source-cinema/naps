import numpy as np


def interleave(*args):
    n = len(args)
    w, h = args[0].shape
    a = np.zeros((w * n, h))
    for i, arg in enumerate(args):
        a[i::n] = arg
    return a


def full_width(w, stages):
    return int(width_factor(stages) * w)


def width_factor(stages, factor=1.0):
    if stages == 1:
        return 2 * factor
    else:
        return factor * 3 / 2 + width_factor(stages - 1, factor / 2)


def real_width(encoded_width, stages):
    factor = width_factor(stages)
    return int(encoded_width // factor)


def pack(image, levels):
    h, w = image.shape
    result = np.zeros((h, full_width(w, levels)), dtype=image.dtype)
    orig_result = result

    for level in reversed(range(levels)):
        hf1 = image[:h // 2, w // 2:]
        hf2 = image[h // 2:, :w // 2]
        hf3 = image[h // 2:, w // 2:]

        result[:h // 2, -w * 3 // 2:-w * 2 // 2] = hf1
        result[:h // 2, -w * 2 // 2:-w * 1 // 2] = hf2
        result[:h // 2, -w * 1 // 2:] = hf3

        if level == 0:
            result[:h // 2, :w // 2] = image[:h // 2, :w // 2]
        else:
            result = result[5::2, :-w * 3 // 2]
            image = image[:h // 2, :w // 2]
            w //= 2
            h //= 2

    return orig_result


def unpack(image, levels):
    h, w = image.shape
    w = real_width(w, levels)
    result = np.zeros((h, w), dtype=image.dtype)
    orig_result = result

    for level in reversed(range(levels)):
        hf1 = image[:h // 2, -w * 3 // 2: -w * 2 // 2]
        hf2 = image[:h // 2, -w * 2 // 2: -w * 1 // 2]
        hf3 = image[:h // 2, -w * 1 // 2:]
        result[:h // 2, w // 2:] = hf1
        result[h // 2:, :w // 2] = hf2
        result[h // 2:, w // 2:] = hf3

        if level == 0:
            result[:h // 2, :w // 2] = image[:h // 2, :w // 2]
        else:
            result = result[:h // 2, :w // 2]
            image = image[5::2, :-w * 3 // 2]
            w //= 2
            h //= 2

    return orig_result
