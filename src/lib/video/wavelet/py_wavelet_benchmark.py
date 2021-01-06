import sys
from itertools import product
from multiprocessing import Pool

import numpy as np
import rawpy
from PIL import Image

from lib.video.wavelet.py_compressor import compress
from lib.video.wavelet.py_wavelet import psnr, inverse_multi_stage_wavelet2d, multi_stage_wavelet2d, ty
from lib.video.wavelet.py_wavelet_repack import pack, unpack
from util.plot_util import plt_image, plt_show, plt_hist

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'usage:\n{sys.argv[0]} <input_file>')
        exit(1)
    _, input_file = sys.argv
    if input_file.endswith(".dng"):
        image = rawpy.imread(input_file)
        color_images = [
            image.raw_image[0::2, 0::2],
            image.raw_image[0::2, 1::2],
            image.raw_image[1::2, 0::2],
            image.raw_image[1::2, 1::2],
        ]
        bit_depth = 12
    else:
        color_images = [np.array(Image.open(sys.argv[1])).astype(ty)]
        bit_depth = 8
    h, w = color_images[0].shape


    def each(coefficients):
        a, b, c, d, e, f, g = [1 if c == 0 else c for c in coefficients]
        quantization = [
            [1, a, a, b],
            [1, c, c, d],
            [g, e, e, f],
        ]

        transformed = [multi_stage_wavelet2d(image, 3, quantization=quantization) for image in color_images]

        compressed = compress(transformed[0], 3, bit_depth=bit_depth)

        roundtripped = [inverse_multi_stage_wavelet2d(t, 3) for t in transformed]

        if False:
            plt_image("orig", color_images[0], cmap="gray")
            plt_image("roundtripped", roundtripped[0], cmap="gray")
            plt_image("diff", roundtripped[0][16:-16, 16:-16] - color_images[0][16:-16, 16:-16], vmin=-2, vmax=2, cmap="bwr")
            plt_show()

        if False:
            reference_frame = fill_reference_frame(h, w, levels=3)
            plt_image("reference", unpack(pack(reference_frame, 3), 3))
            plt_image("input", color_images[0])
            for v in np.unique(reference_frame):
                values = transformed[0][np.where(reference_frame == v)]
                print(f'{v}\t{np.min(values)}\t{np.max(values)}')
                plt_hist(str(v), values, bins=200)

                avrg = np.mean(values)
                stdev = np.std(values)
                print(f'avrg: {avrg}; stdev: {stdev}')
                outliers_base = np.copy(reference_frame)
                outliers_base[np.where((outliers_base == v) & (np.abs(transformed[0] - avrg) > 5 * stdev))] = 500
                plt_image(f"outliers {v}", outliers_base)
            plt_show()

        resulting_psnr = np.mean([psnr(image[16:-16, 16:-16], r[16:-16, 16:-16], bit_depth=bit_depth) for image, r in zip(color_images, roundtripped)])
        print(f'{a}\t{b}\t{c}\t{d}\t{e}\t{f}\t{g}\t{resulting_psnr}')

    each((64, 64, 64, 64, 64, 64, 1))
    # pool = Pool(1)
    # todo = np.array(list(product(*([[1, 2, 4, 8, 12, 16, 20, 24, 32, 40, 48]] * 6), [1, 2, 4])))
    # np.random.shuffle(todo)
    # pool.map(each, todo)
