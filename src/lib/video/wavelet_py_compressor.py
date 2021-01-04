import numpy as np
import sys
from PIL import Image
import os
from os.path import join
import matplotlib.pyplot as plt

from lib.video.wavelet_decompressor import inverse_wavelet_3

bit_modifier = 65535
ty = np.int16
save_ty = np.uint16


def wavelet1d(image):
    def px(i):
        k = np.roll(image, -i, 0)
        return k[::2]

    lf_part = px(0) + px(1)
    hf_part = (px(0) - px(1)) + (-px(-2) - px(-1) + px(2) + px(3) + 4) // 8

    return lf_part, hf_part


def wavelet2d(image):
    width = len(image[0])
    lf_part, hf_part = wavelet1d(image)
    lf_part, hf_part = wavelet1d(np.hstack([lf_part, hf_part]).T)
    lf_part = lf_part.T
    hf_part = hf_part.T
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


lf_parts = []


def multi_stage_wavelet2d(image, stages):
    h, w = image.shape
    global lf_parts
    lf_parts = [image]

    def multi_stage_wavelet2d_impl(result, image, stages):
        h, w = image.shape
        lf_part, *hf_part = wavelet2d(image)
        lf_parts.append(lf_part)
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
        template[:ch, :cw] = 254
        template[ch:, cw:] = 254
        image = np.tile(template, (h // ch, w // ch))
    elif input_file == 'gradient':
        w = h = 256
        image = np.array([[(x * y) % 256 for x in range(w)] for y in range(h)]).astype(np.uint8)
    elif input_file == 'noise':
        image = np.random.randint(0, 255, (256, 256), np.uint8)
    elif input_file == '127':
        w = h = 256
        image = np.array([[0 if y % 2 == 127 else 126] * w for y in range(h)])
    else:
        image = np.array(Image.open(sys.argv[1]))
    image = image.astype(np.int16)

    encoded = multi_stage_wavelet2d(image, 3)
    h, w = encoded.shape

    # os.makedirs(output_dir, exist_ok=True)
    # Image.fromarray(image).save(join(output_dir, "ref.png"))
    # Image.fromarray((encoded[:h // 2] + bit_modifier // 2).astype(save_ty)).save(join(output_dir, "0.png"))
    # Image.fromarray((encoded[h // 2:] + bit_modifier // 2).astype(save_ty)).save(join(output_dir, "1.png"))

    lf_decoded = inverse_wavelet_3(encoded, return_lf_parts=True)

    for i, (a, b) in enumerate(zip(lf_parts, lf_decoded)):
        crop = 16
        a_crop = a[crop:-crop, crop:-crop]
        b_crop = b[crop:-crop, crop:-crop]
        diff = a_crop - b_crop

        print(f"psnr {i}: {10 * np.log10(256**2 / np.sum(diff**2) * diff.size)}")

        plt.figure()
        plt.title(f"lf diff {i}")
        plt.imshow(diff, cmap="bwr", vmin=-2, vmax=+2)

        plt.figure()
        plt.title(f"lf enc {i}")
        plt.imshow(a_crop, cmap="gray", vmin=0, vmax=255 * 2**i)

        plt.figure()
        plt.title(f"lf dec {i}")
        plt.imshow(b_crop, cmap="gray", vmin=0, vmax=255 * 2**i)


        def hist(data):
            min = np.min(data)
            max = np.max(data)
            plt.bar(np.arange(min, max + 1), np.bincount(np.ravel(data) - min), width=1.0)

        if i == 0:
            diff_values = a_crop[np.where(diff != 0)]

            plt.figure()
            plt.title(f"diff enc hist {i}")
            plt.bar(range(256), np.bincount(diff_values, minlength=256), width=1.0)

            plt.figure()
            plt.title(f"diff hist {i}")
            hist(diff)

            plt.figure()
            plt.title(f"lf hist enc {i}")
            hist(a_crop)

            plt.figure()
            plt.title(f"lf hist dec {i}")
            hist(b_crop)
    plt.show()
