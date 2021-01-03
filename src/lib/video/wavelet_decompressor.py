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
    hf_part = np.pad(hf_part, pad_width, constant_values=0.5)

    x, y = lf_part.shape
    res = np.zeros((x * 2, y), dtype=ty)
    res[0::2] = ((np.roll(lf_part, -1, 0) - np.roll(lf_part, +1, 0) + 4) // 8 + hf_part + lf_part)
    res[1::2] = ((-np.roll(lf_part, -1, 0) + np.roll(lf_part, +1, 0) + 4) // 8 - hf_part + lf_part)

    if pad_width > 0:
        return res[2 * pad_width:-2 * pad_width, pad_width:-pad_width]
    else:
        return res


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'usage:\n{sys.argv[0]} <input_dir>')
        exit(1)
    _, input_dir = sys.argv

    a = (np.array(Image.open(join(input_dir, "0.png"))).astype(ty) - bit_modifier // 2)
    b = (np.array(Image.open(join(input_dir, "1.png"))).astype(ty) - bit_modifier // 2)
    image = np.vstack([a, b])

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

    lf_stage3_y = inverse_wavelet(np.hstack([lf_stage3, hf_stage3[:, ::3]]), np.hstack([hf_stage3[:, 1::3], hf_stage3[:, 2::3]]))
    lf_stage2 = inverse_wavelet(lf_stage3_y.T[:width // 8], lf_stage3_y.T[width // 8:], 0).T

    lf_stage2_y = inverse_wavelet(np.hstack([lf_stage2, hf_stage2[:, ::3]]), np.hstack([hf_stage2[:, 1::3], hf_stage2[:, 2::3]]))
    lf_stage1 = inverse_wavelet(lf_stage2_y.T[:width // 4], lf_stage2_y.T[width // 4:], 0).T

    lf_stage1_y = inverse_wavelet(np.hstack([lf_stage1, hf_stage1[:, ::3]]), np.hstack([hf_stage1[:, 1::3], hf_stage1[:, 2::3]]))
    lf_stage0 = inverse_wavelet(lf_stage1_y.T[:width // 2], lf_stage1_y.T[width // 2:], 0).T

    plt.figure()
    plt.title("decoded")
    print(np.min(lf_stage0), np.max(lf_stage0))
    plt.imshow(lf_stage0, cmap="gray", vmin=0, vmax=255)
    plt.figure()
    ref = np.array(Image.open(join(input_dir, "ref.png")))
    plt.title("ref")
    plt.imshow(ref, cmap="gray", vmin=0, vmax=255)
    plt.figure()
    plt.title("diff")
    crop = 16
    plt.imshow((lf_stage0 - ref)[crop:-crop, crop:-crop], cmap="bwr")
    plt.colorbar()
    plt.show()
