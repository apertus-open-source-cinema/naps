"""Allows for non hierarchical connections in a hierarchical design.

This is useful for numerous things:
1. Give parameters to modules, no matter, where they are in the hierarchy.
2. Give AXI ports or other ZYNQ resources to modules without much overhead.
"""

from nmigen import *

params = {}
done = False


def param(name, width):
    assert not done

    signal = Signal(width)
    params[name] = signal
    return signal


def add_params(module):
    global done
    assert not done

    for name, signal in params.items():
        setattr(module, name, signal)
    done = True
