import sys
from itertools import product

import numpy as np
import rawpy

from lib.video.wavelet.py_wavelet import psnr

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'usage:\n{sys.argv[0]} <input_file>')
        exit(1)
    _, input_file = sys.argv
    image = rawpy.imread(input_file)
    color_images = [
        image.raw_image[0::2, 0::2],
        image.raw_image[0::2, 1::2],
        image.raw_image[1::2, 0::2],
        image.raw_image[1::2, 1::2],
    ]

    for a, b, c in product(range(1, 11), range(1, 21, 2), range(1, 41, 4)):
        quantization = [
            [1, a, a, a],
            [1, b, b, b],
            [1, c, c, c],
        ]

        resulting_psnr = np.mean([psnr(image, 3, quantization) for image in color_images])
        print(f'{a}\t{b}\t{c}\t{resulting_psnr}')
