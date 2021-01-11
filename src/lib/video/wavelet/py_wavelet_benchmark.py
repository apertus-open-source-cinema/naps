import sys
from bz2 import BZ2File
from collections import defaultdict
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
            color_numbers = defaultdict(int)
            for channel in image.color_desc.decode("utf-8"):
                color_numbers[channel] += 1
                filenames.append(f'{filename}--{channel}{color_numbers[channel]}')
            assert bit_depth is None or bit_depth == 12
            bit_depth = 12
        else:
            images += [np.array(Image.open(sys.argv[1])).astype(ty)]
            filenames += [filename]
            assert bit_depth is None or bit_depth == 8
            bit_depth = 8

    output_dir = Path("analyze")
    output_dir.mkdir(exist_ok=True, parents=True)

    def each(params):
        (filename, image), coefficients = params
        a, b, c, d, e, f, g = [1 if c == 0 else c for c in coefficients]
        quantization = [
            [1, a, a, b],
            [1, c, c, d],
            [g, e, e, f],
        ]

        transformed = multi_stage_wavelet2d(image, levels, quantization=quantization)
        compressed, symbol_frequencies, rle_ratio, huffman_ratio, total_ratio = compress(transformed, levels, bit_depth=bit_depth)
        roundtripped = inverse_multi_stage_wavelet2d(transformed, levels)
        psnr = compute_psnr(image[16:-16, 16:-16], roundtripped[16:-16, 16:-16], bit_depth=bit_depth)

        print(f'{filename}\t{psnr=:.03f}\t{rle_ratio=:.03f}\t{huffman_ratio=:.03f}\t{total_ratio=:.03f}')

        with BZ2File(output_dir / f'{"-".join("{:02d}".format(i) for i in chain(*quantization))}-{filename}.pckl.bz2', 'wb') as f:
            dump({
                "files": filename,
                "quantization": quantization,
                "psnr": psnr,
                "rle_ratio": rle_ratio,
                "symbol_frequency": symbol_frequencies,
            }, f)

        return psnr, rle_ratio, symbol_frequencies

    todo = list(product(zip(filenames, images), [[128, 128, 128, 128, 128, 128, 4]]))

    pool = Pool(8)

    use_progress = False
    if use_progress:
        progress_file = (output_dir / "progress.txt")
        try:
            progress = int(progress_file.read_text())
        except FileNotFoundError:
            progress = 0
    else:
        progress = 0

    for i, _ in enumerate(pool.imap(each, todo[progress:])):
        if use_progress:
            progress_file.write_text(str(i))
