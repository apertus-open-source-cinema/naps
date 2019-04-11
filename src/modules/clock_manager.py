"""A singleton from which you can request clocks with an arbitrary speed"""

import re
from nmigen import *

clocks = {}


def get_clock(requested_freq):
    """Returns a clock with the requested frequency

    Possible frequency definitions include: `1Mhz`, `1e6`, `0.1 Ghz`
    """
    try:
        freq = int(requested_freq)
    except ValueError:
        freq = _freq_to_int(requested_freq)
    if requested_freq not in clocks:
        clocks[requested_freq] = Signal()
    return clocks[requested_freq]


def manage_clocks(module):
    """Instanciates the clocking ressources (e.g. PLLs)"""
    raise NotImplementedError


def _freq_to_int(freq):
    match = re.match("([\d.]+) ?([gmk])(hz)?", freq.lower())
    return int(float(match[1]) * ({"k": 1e3, "m": 1e6, "g": 1e9}[match[2]]))
