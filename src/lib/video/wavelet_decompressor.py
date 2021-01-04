from PIL import Image
import matplotlib.pyplot as plt
import numpy as np
import sys
from os.path import join

bit_modifier = 65535
ty = np.int16
save_ty = np.uint16


# always along first axis
def inverse_wavelet(lf_part, hf_part, pad_width=0):
    lf_part = np.pad(lf_part, pad_width, "edge")
    hf_part = np.pad(hf_part, pad_width, constant_values=bit_modifier // 2)

    x, y = lf_part.shape
    res = np.zeros((x * 2, y), dtype=ty)
    res[0::2] = (((np.roll(lf_part, +1, 0) - np.roll(lf_part, -1, 0) + 4) >> 3) + hf_part + lf_part) >> 1
    res[1::2] = (((-np.roll(lf_part, +1, 0) + np.roll(lf_part, -1, 0) + 4) >> 3) - hf_part + lf_part) >> 1

    if pad_width > 0:
        return res[2 * pad_width:-2 * pad_width, pad_width:-pad_width]
    else:
        return res


def unpack(image):
    encoded_width = len(image[0])
    encoded_height = len(image) // 2
    height = encoded_height * 2
    width = int(encoded_width // 2.75)

    hf_stage1 = image[:height // 2, -width * 3 // 2:]
    image = image[5::2, :-width * 3 // 2]
    hf_stage2 = image[:height // 4, -width * 3 // 4:]

    image = image[5::2, :-width * 3 // 4]
    hf_stage3 = image[:height // 8, -width * 3 // 8:]
    lf_stage3 = image[:height // 8, :width // 8]

    return lf_stage3, hf_stage3, hf_stage2, hf_stage1


def inverse_wavelet_stage(lf, hf, pad_width=0):
    h, w = lf.shape
    y_transformed = inverse_wavelet(np.hstack([lf, hf[:, 0::3]]), np.hstack([hf[:, 1::3], hf[:, 2::3]]))
    return inverse_wavelet(y_transformed.T[:w], y_transformed.T[w:], pad_width).T


def inverse_wavelet_3(image, return_lf_parts=False):
    lf_stage3, hf_stage3, hf_stage2, hf_stage1 = unpack(image)
    lf_stage2 = inverse_wavelet_stage(lf_stage3, hf_stage3)
    lf_stage1 = inverse_wavelet_stage(lf_stage2, hf_stage2)
    decoded = inverse_wavelet_stage(lf_stage1, hf_stage1)
    if return_lf_parts:
        return decoded, lf_stage1, lf_stage2, lf_stage3
    return decoded


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'usage:\n{sys.argv[0]} <input_dir>')
        exit(1)
    _, input_dir = sys.argv

    a = (np.array(Image.open(join(input_dir, "0.png"))).astype(ty) - bit_modifier // 2)
    b = (np.array(Image.open(join(input_dir, "1.png"))).astype(ty) - bit_modifier // 2)
    image = np.vstack([a, b])

    lf_stage3, hf_stage3, hf_stage2, hf_stage1 = unpack(image)
    lf_stage2 = inverse_wavelet_stage(lf_stage3, hf_stage3)
    lf_stage1 = inverse_wavelet_stage(lf_stage2, hf_stage2)
    decoded = inverse_wavelet_stage(lf_stage1, hf_stage1)

    plt.figure()
    plt.title("decoded")
    print(np.min(decoded), np.max(decoded))
    plt.imshow(decoded, cmap="gray", vmin=0, vmax=255)

    plt.figure()
    ref = np.array(Image.open(join(input_dir, "ref.png")))
    plt.title("ref")
    plt.imshow(ref, cmap="gray", vmin=0, vmax=255)

    plt.figure()
    plt.title("diff")
    crop = 16
    plt.imshow((decoded - ref)[crop:-crop, crop:-crop], cmap="bwr", vmin=-2, vmax=+2)
    plt.colorbar()
    plt.show()
