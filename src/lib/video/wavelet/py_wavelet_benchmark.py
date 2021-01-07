import sys
from bz2 import BZ2File
from itertools import product, chain
from multiprocessing import Pool
from pathlib import Path
from pickle import dump

import numpy as np
import rawpy
from PIL import Image
from tqdm import tqdm

from lib.video.wavelet.py_compressor import compress, uncompress, empty_symbol_frequencies_dict
from lib.video.wavelet.py_wavelet import compute_psnr, inverse_multi_stage_wavelet2d, multi_stage_wavelet2d, ty

levels = 3

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'usage:\n{sys.argv[0]} input...')
        exit(1)
    _, *files = sys.argv

    filenames = []
    images = []
    bit_depth = None
    for f in files:
        filename = Path(f).stem
        if f.endswith(".dng"):
            image = rawpy.imread(f)
            images += [
                image.raw_image[0::2, 0::2],
                image.raw_image[0::2, 1::2],
                image.raw_image[1::2, 0::2],
                image.raw_image[1::2, 1::2],
            ]
            filenames += [
                f'{filename}--top-left',
                f'{filename}--top-right',
                f'{filename}--bottom-left',
                f'{filename}--bottom-right'
            ]
            assert bit_depth is None or bit_depth == 12
            bit_depth = 12
        else:
            images += [np.array(Image.open(sys.argv[1])).astype(ty)]
            filenames += [filename]
            assert bit_depth is None or bit_depth == 8
            bit_depth = 8

    output_dir = Path("analyze")
    output_dir.mkdir(exist_ok=True, parents=True)

    def each_image(filename, image, quantization):
        transformed = multi_stage_wavelet2d(image, levels, quantization=quantization)
        compressed, symbol_frequencies, rle_ratio = compress(transformed, levels, bit_depth=bit_depth)
        roundtripped = inverse_multi_stage_wavelet2d(transformed, levels)
        psnr = compute_psnr(image[16:-16, 16:-16], roundtripped[16:-16, 16:-16], bit_depth=bit_depth)

        with BZ2File(output_dir / f'{"-".join("{:02d}".format(i) for i in chain(*quantization))}-{filename}.pckl.bz2', 'wb') as f:
            dump({
                "files": filename,
                "quantization": quantization,
                "psnr": psnr,
                "rle_ratio": rle_ratio,
                "symbol_frequency": symbol_frequencies,
            }, f)

        return psnr, rle_ratio, symbol_frequencies


    def each_coefficient_set(coefficients):
        a, b, c, d, e, f, g = [1 if c == 0 else c for c in coefficients]
        quantization = [
            [1, a, a, b],
            [1, c, c, d],
            [g, e, e, f],
        ]

        psnrs = []
        rle_ratios = []
        symbol_frequencies = []
        for image, filename in zip(images, filenames):
            psnr, rle_ratio, freqs = each_image(filename, image, quantization)
            symbol_frequencies.append(freqs)
            rle_ratios.append(rle_ratio)
            psnrs.append(psnr)

    pool = Pool(8)
    todo = np.array(list(product(*([[1, 8, 16, 32, 48]] * 6), [1, 4])))
    np.random.RandomState(0).shuffle(todo)
    progress_file = (output_dir / "progress.txt")
    try:
        progress = int(progress_file.read_text())
    except FileNotFoundError:
        progress = 0
    for i, _ in enumerate(tqdm(pool.imap(each_coefficient_set, todo[progress:]), total=len(todo), initial=progress)):
        progress_file.write_text(str(i))
