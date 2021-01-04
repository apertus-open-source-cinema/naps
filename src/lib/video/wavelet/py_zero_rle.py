import numpy as np


def zero_rle(array):
    indices = np.where(array == 0)
    print(indices)
