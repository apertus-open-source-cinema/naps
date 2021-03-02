#!/usr/bin/env python3

from setuptools import setup, find_packages
from pathlib import Path

def scm_version():
    def local_scheme(version):
        if version.tag and not version.distance:
            return version.format_with("")
        else:
            return version.format_choice("", "")
    return {
        "relative_to": __file__,
        "version_scheme": "guess-next-dev",
        "local_scheme": local_scheme
    }


setup(
    name='naps',
    use_scm_version=scm_version(),
    url='https://github.com/apertus-open-source-cinema/nmigen-gateware',
    description='nMigen Apertus Packages',
    long_description=Path("README.rst").read_text(),
    packages=find_packages(),
    install_requires=[
        'huffman',
        'nmigen @ git+https://github.com/nmigen/nmigen.git',
        'nmigen-boards @ git+https://github.com/nmigen/nmigen-boards.git',
    ],
    keywords='nmigen apertus fpga gateware video camera',
    project_urls={
        'Documentation': 'https://apertus-open-source-cinema.github.io/nmigen-gateware/',
        'Homepage': 'https://github.com/apertus-open-source-cinema/nmigen-gateware',
        'Bug Tracker': 'https://github.com/apertus-open-source-cinema/nmigen-gateware/issues'
    },
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
