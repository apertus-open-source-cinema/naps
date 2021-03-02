import numpy as np
import sys
from PIL import Image
from naps.util.plot_util import plt_discrete_hist, plt_image, plt_show

ty = np.int32


def wavelet1d(image, direction_x=False):
    img = image.T if direction_x else image
    cache_dict = {}

    def px(i):
        i2 = i // 2
        if i2 not in cache_dict:
            cache_dict[i2] = np.roll(img, -i2 * 2, 0) if i != 0 else img
        return cache_dict[i2][i % 2::2]

    lf_part = px(0) + px(1)
    hf_part = (px(0) - px(1)) + (-px(-2) - px(-1) + px(2) + px(3) + 4) // 8
    out = np.empty_like(image)
    h, w = out.shape
    if direction_x:
        out[:, :w // 2] = lf_part.T
        out[:, w // 2:] = hf_part.T
    else:
        out[:h // 2] = lf_part
        out[h // 2:] = hf_part
    return out


def inverse_wavelet_1d(image, pad_width=0, direction_x=False):
    img = image.T if direction_x else image
    h, w = img.shape
    lf_part = np.pad(img[:h // 2], pad_width, "edge")
    hf_part = np.pad(img[h // 2:], pad_width, constant_values=0)

    x, y = lf_part.shape
    res = np.zeros((x * 2, y), dtype=ty)
    res[0::2] = (((np.roll(lf_part, +1, 0) - np.roll(lf_part, -1, 0) + 4) >> 3) + hf_part + lf_part) >> 1
    res[1::2] = (((-np.roll(lf_part, +1, 0) + np.roll(lf_part, -1, 0) + 4) >> 3) - hf_part + lf_part) >> 1

    pad_crop = res[2 * pad_width:-2 * pad_width, pad_width:-pad_width] if pad_width > 0 else res
    return pad_crop.T if direction_x else pad_crop


def quantize(image, values, level):
    h, w = image.shape
    parts = [image[:h // 2, :w // 2], image[:h // 2, w // 2:], image[h // 2:, :w // 2], image[h // 2:, w // 2:]]
    for i, (part, value) in enumerate(zip(parts, values)):
        part[:] = np.round(part / value)


def dequantize(image, values, level):
    h, w = image.shape
    parts = [image[:h // 2, :w // 2], image[:h // 2, w // 2:], image[h // 2:, :w // 2], image[h // 2:, w // 2:]]
    for i, (part, value) in enumerate(zip(parts, values)):
        part[:] = part * value


def wavelet2d(image):
    x_transformed = wavelet1d(image, direction_x=True)
    xy_transformed = wavelet1d(x_transformed)
    return xy_transformed


def inverse_wavelet_2d(image, pad_width=0):
    y_transformed = inverse_wavelet_1d(image, pad_width)
    return inverse_wavelet_1d(y_transformed, pad_width, direction_x=True)


def multi_stage_wavelet2d(image, stages, return_all_stages=False, quantization=None):
    h, w = image.shape
    stages_outputs = [image.astype(ty)]
    for i in range(stages):
        transformed = np.copy(stages_outputs[-1])
        transformed[:h // 2 ** i, :w // 2 ** i] = wavelet2d(transformed[:h // 2 ** i, :w // 2 ** i])
        if quantization is not None:
            quantize(transformed[:h // 2 ** i, :w // 2 ** i], quantization[i], i)
        stages_outputs.append(transformed)
    return stages_outputs if return_all_stages else stages_outputs[-1]


def inverse_multi_stage_wavelet2d(image, stages, return_all_stages=False, quantization=None):
    h, w = image.shape
    stages_outputs = [image]
    for i in reversed(range(stages)):
        transformed = np.copy(stages_outputs[-1])
        if quantization is not None:
            dequantize(transformed[:h // 2 ** i, :w // 2 ** i], quantization[i], i)
        transformed[:h // 2 ** i, :w // 2 ** i] = inverse_wavelet_2d(transformed[:h // 2 ** i, :w // 2 ** i])
        stages_outputs.append(transformed)
    return stages_outputs if return_all_stages else stages_outputs[-1]


def compute_psnr(a, b, bit_depth=8):
    diff = a - b
    old_err_state = np.seterr(divide='ignore')
    psnr = 10 * np.log10(((2 ** bit_depth) - 1) ** 2 / np.sum(diff ** 2) * diff.size)
    np.seterr(**old_err_state)
    return psnr


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'usage:\n{sys.argv[0]} <input_file>')
        exit(1)
    _, input_file = sys.argv

    if input_file == 'test':
        w = h = 32
        cw = ch = h // 32
        template = np.zeros((2 * ch, 2 * cw), dtype=ty)
        template[:ch, :cw] = 254
        template[ch:, cw:] = 254
        image = np.tile(template, (h // ch, w // ch))
    else:
        image = np.array(Image.open(sys.argv[1])).astype(ty)
    image = image

    quantization = [
        [1, 64, 64, 64],
        [1, 64, 64, 64],
        [1, 64, 64, 64],
    ]

    stages_encode = multi_stage_wavelet2d(image, 3, return_all_stages=True, quantization=quantization)
    stages_decode = inverse_multi_stage_wavelet2d(stages_encode[-1], 3, return_all_stages=True, quantization=quantization)

    plot = True
    for i, (a, b) in enumerate(zip(stages_encode, reversed(stages_decode))):
        crop = 16
        a_crop = a[crop:-crop, crop:-crop]
        b_crop = b[crop:-crop, crop:-crop]
        diff = a_crop - b_crop

        print(f"psnr level {i}: {compute_psnr(a_crop, b_crop)}")

        if plot:
            plt_image(f"lf diff {i}", diff, cmap="bwr", vmin=-2, vmax=+2)
            plt_image(f"lf enc {i}", np.log(a_crop))
            plt_image(f"lf dec {i}", b_crop, cmap="bwr", vmin=-5, vmax=5)

            if i == 0:
                diff_values = a_crop[np.where(diff != 0)]
                plt_discrete_hist(f"diff hist {i}", diff)
                plt_discrete_hist(f"lf hist enc {i}", a_crop)
                plt_discrete_hist(f"lf hist dec {i}", b_crop)
    plt_show()
