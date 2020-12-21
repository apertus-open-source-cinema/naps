import matplotlib.image as im
import matplotlib.pyplot as plt
import numpy as np
import sys

a = im.imread(sys.argv[1] + "0.png")
b = im.imread(sys.argv[1] + "1.png")
image = np.vstack([a, b])

encoded_width = len(image[0])
encoded_height = len(image) // 2
height = encoded_height * 2
width = int(encoded_width // 2.75)

# plt.figure()
# plt.imshow(image)

hf_stage1 = image[:height // 2, -width * 3 // 2:]
image = image[5::2, :-width * 3 // 2]
hf_stage2 = image[:height // 4, -width * 3 // 4:]

image = image[5::2, :-width * 3 // 4]
hf_stage3 = image[:height // 8, -width * 3 // 8:]
lf_stage3 = image[:height // 8, :width // 8]

# always along first axis
def inverse_wavelet(lf_part, hf_part, pad_width = 0):
    lf_part = np.pad(lf_part, pad_width, "edge")
    hf_part = np.pad(hf_part, pad_width, constant_values=0.5)

    x, y = lf_part.shape
    res = np.zeros((x * 2, y))
    res[::2] = lf_part
    res[1::2] = lf_part
    correction = hf_part - 0.5 + (np.roll(lf_part, -1, 0) - np.roll(lf_part, +1, 0)) / 4

    # correction /= 2
    # plt.figure()
    # plt.title("correction")
    # plt.imshow(correction, cmap="gray")
    # plt.colorbar()

    res[0::2] -= correction
    res[1::2] += correction

    if pad_width > 0:
        return res[2*pad_width:-2*pad_width,pad_width:-pad_width]
    else:
        return res

    # lf_i = px(2*i) + px(2*i + 1) // 2
    # hf_i = ((px(2*i) - px(2*i + 1) + (-(px(2(i - 1)) + px(2(i - 1) + 1) + px(2*(i + 1)) + px(2*(i + 1) + 1))) // 8) // 2) + 128 # (2**len(self.input.payload) // 2)

    # g_i = (px(2*i) - px(2*i + 1)) // 2 = hf_i + lf_(i - 1) // 8 + lf(i + 1) // 8

    # px(2*i) = lf_i + g_i
    # px(2*i + 1) = lf_i - g_i

lf_stage3_y = inverse_wavelet(np.hstack([lf_stage3, hf_stage3[:,::3]]), np.hstack([hf_stage3[:,1::3], hf_stage3[:,2::3]]))
lf_stage2 = inverse_wavelet(lf_stage3_y.T[:width//8], lf_stage3_y.T[width//8:]).T

lf_stage2_y = inverse_wavelet(np.hstack([lf_stage2, hf_stage2[:,::3]]), np.hstack([hf_stage2[:,1::3], hf_stage2[:,2::3]]))
lf_stage1 = inverse_wavelet(lf_stage2_y.T[:width//4], lf_stage2_y.T[width//4:]).T

lf_stage1_y = inverse_wavelet(np.hstack([lf_stage1, hf_stage1[:,::3]]), np.hstack([hf_stage1[:,1::3], hf_stage1[:,2::3]]))
lf_stage0 = inverse_wavelet(lf_stage1_y.T[:width//2], lf_stage1_y.T[width//2:]).T

plt.figure()
plt.imshow(np.vstack([np.hstack([lf_stage1, hf_stage1[:,::3]]), np.hstack([hf_stage1[:,1::3], hf_stage1[:,2::3]])]), cmap = "gray")

# plt.figure()
# plt.imshow(lf_stage0, cmap="gray", vmin=0.0, vmax=1.0)
# plt.show()
plt.show()
