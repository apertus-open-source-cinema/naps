"""A singleton from which you can request clocks with an arbitrary speed

The clock manager itself is hardware independent, but it uses a hardware dependent clock solver to generate the
clocking tree.
"""

import re

from modules.clocking.clock_solver import ClockSolver
from modules.clocking.future_int import FutureInt

clocks = {}


def generate_clock(requested_freq, name):
    """Gerenates a clock with the requested frequency
    Possible frequency definitions include: `1Mhz`, `1e6`, `0.1 Ghz` and LazyInt

    :returns a LazyInt object, that represents the actual generated frequency
    """
    requested_freq = _freq_to_int(requested_freq)

    if name not in clocks:
        clocks[name] = (requested_freq, FutureInt())
    return clocks[name][1]


def manage_clocks(module, clk, f_in):
    """Instantiates the clocking resources (e.g. PLLs)

    This should be called exactly once from the top level after everything else
    """
    module.submodules.clock_solver = ClockSolver(clocks, clk, _freq_to_int(f_in))


def _freq_to_int(freq):
    if isinstance(freq, FutureInt):
        return freq
    try:
        return int(freq)
    except ValueError:
        match = re.match("([\d.]+) ?([gmk])(hz)?", freq.lower())
        if not match:
            raise ValueError("parameter {} could not be decoded as a frequency".format(freq))
        return int(float(match[1]) * ({"k": 1e3, "m": 1e6, "g": 1e9}[match[2]]))
