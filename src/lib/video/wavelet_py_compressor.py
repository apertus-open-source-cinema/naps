import numpy as np
import sys
from PIL import Image
import os
from os.path import join

bit_modifier = 65535
ty = np.int16
save_ty = np.uint16


def wavelet1d(image):
    def lf(i):
        k = np.roll(image, 2 * i, 0)
        return (k[0::2] + k[1::2])

    lf_part = lf(0) / 2
    hf_part = (image[0::2] - image[1::2] + (-lf(-1) + lf(1)) / 8) / 2 + 0.5
    return lf_part, hf_part


def wavelet2d(image):
    width = len(image[0])
    lf_part, hf_part = wavelet1d(image)

    lf_part, hf_part = wavelet1d(np.hstack([lf_part, hf_part]).T)
    # print(lf_part[4,4])
    lf_part = lf_part.T
    hf_part = hf_part.T
    # plt.imshow(np.vstack([np.hstack([lf_part[:, :width // 2], hf_part[:, :width // 2]]), np.hstack([lf_part[:, width // 2:], hf_part[:, width // 2:]])]))
    # plt.show()
    return lf_part[:, :width // 2], hf_part[:, :width // 2], lf_part[:, width // 2:], hf_part[:, width // 2:]


def interleave(*args):
    n = len(args)
    w, h = args[0].shape
    a = np.zeros((w * n, h), dtype=ty)
    for i, arg in enumerate(args):
        a[i::n] = arg
    return a


def full_width(w, stages):
    if stages == 1:
        return w * 2
    else:
        return w * 3 // 2 + full_width(w // 2, stages - 1)


def multi_stage_wavelet2d(image, stages):
    h, w = image.shape

    def multi_stage_wavelet2d_impl(result, image, stages):
        h, w = image.shape
        lf_part, *hf_part = wavelet2d(image)
        if stages == 1:
            result[:h // 2] = np.hstack([lf_part, interleave(*[hf.T for hf in hf_part]).T])
        else:
            result[:h // 2, -w * 3 // 2:] = interleave(*[hf.T for hf in hf_part]).T
            multi_stage_wavelet2d_impl(result[5::2, :-w * 3 // 2], lf_part, stages - 1)
        return result

    result = np.zeros((h, full_width(w, stages)), dtype=ty)
    return multi_stage_wavelet2d_impl(result, image, stages)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'usage:\n{sys.argv[0]} <input_file> <output_dir>')
        exit(1)
    _, input_file, output_dir = sys.argv

    if input_file == 'test':
        w = h = 32
        cw = ch = h // 32
        template = np.zeros((2 * ch, 2 * cw), dtype=np.uint8)
        template[:ch, :cw] = 255
        template[ch:, cw:] = 255
        image = np.tile(template, (h // ch, w // ch))
    else:
        image = np.array(Image.open(sys.argv[1]))

    res = multi_stage_wavelet2d(image.astype(np.int16), 3)
    h, w = res.shape

    os.makedirs(output_dir, exist_ok=True)
    Image.fromarray(image).save(join(output_dir, "ref.png"))
    Image.fromarray((res[:h//2] + bit_modifier//2).astype(save_ty)).save(join(output_dir, "0.png"))
    Image.fromarray((res[h//2:] + bit_modifier//2).astype(save_ty)).save(join(output_dir, "1.png"))
