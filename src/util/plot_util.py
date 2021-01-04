import numpy as np
from matplotlib import pyplot as plt


def plt_discrete_hist(title, data):
    plt.figure()
    plt.title(title)
    min = np.min(data)
    max = np.max(data)
    plt.bar(np.arange(min, max + 1), np.bincount(np.ravel(data) - min, minlength=(max - min)), width=1.0)


def plt_hist(title, data, **kwargs):
    plt.figure()
    plt.title(title)
    plt.hist(np.ravel(data), **kwargs)


def plt_image(title, data, **kwargs):
    plt.figure()
    plt.title(title)
    plt.imshow(data, **kwargs)


def plt_show():
    plt.show()
