#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name='nap',
    version='0.1.0',
    url='http',
    description='nMigen Apertus Packages',
    packages=find_packages(),
    install_requires=[
        'huffman',
        'nmigen @ git+https://github.com/nmigen/nmigen.git',
        'nmigen-boards @ git+https://github.com/nmigen/nmigen-boards.git',
    ],
    extras_require={
        'test': [
            'pytest',
            'pytest-forked',
            'pytest-xdist',
            'psutil',

            'pytest-pycharm',
            'pytest-github-actions-annotate-failures',

            'pydng @ git+https://github.com/schoolpost/PyDNG.git#subdirectory=src',
            'imageio',
            'rawpy',

            'bitarray',


            # needed for python wavelet compressor
            'numba',
            'numpy',

            'scipy',  # only needed for vifp calculation
            'matplotlib',
            'yowasp-yosys',
        ],
        'doc': [
            'sphinx',
            'sphinx_rtd_theme',
        ]
    }
)
