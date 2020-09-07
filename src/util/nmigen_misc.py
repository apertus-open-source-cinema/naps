import math
from functools import reduce
from itertools import count
from typing import Iterator, Iterable

from nmigen import *
from nmigen import Signal
from nmigen.build import ResourceError
from nmigen.hdl.ast import UserValue
from nmigen.hdl.xfrm import TransformedElaboratable


def flatten_nmigen_type(nmigen_things):
    """Flattens a list of signals and records to a list of signals
    :param nmigen_things: A list of signals and records
    :return: A list of signals
    """
    flattened = []
    for signal in nmigen_things:
        if isinstance(signal, Signal):
            flattened += [signal]
        elif isinstance(signal, UserValue):
            flattened += flatten_nmigen_type(signal._lhs_signals())
        elif isinstance(signal, Iterable):
            flattened += flatten_nmigen_type(signal)
    return flattened


def is_nmigen_type(obj):
    """Checks, if an object is a nmigen type or a list of these"""
    if isinstance(obj, (Value, UserValue)):
        return True
    elif not isinstance(obj, str) and isinstance(obj, Iterable):
        return all([is_nmigen_type(elem) for elem in obj])
    else:
        return False


def get_signals(module):
    """Create a list of all signals of a module

    :param module: The module to investigate
    :return A list of property Signals
    """
    if isinstance(module, TransformedElaboratable):
        module = module._elaboratable_
    signals_records = [
        prop for prop
        in [
            getattr(module, name) for name
            in dir(module) if name[0] != "_"
        ]
        if is_nmigen_type(prop)
    ]
    return flatten_nmigen_type(signals_records)


def iterator_with_if_elif(iterator: Iterable, module: Module) -> Iterator:
    """
    A helper to build a priority encoder using If / Elif constructs
    :param iterator: the iterator contaianing all the elements
    :param module: the module from which m.If and m.Elif are sourced
    """
    for i, elem in enumerate(iterator):
        yield (
            module.If if i == 0 else module.Elif,
            elem
        )


def is_pot(x):
    assert int(math.log2(x)) == math.log2(x), "{} is not a power of two".format(x)


def log2(x):
    is_pot(x)
    return int(math.log2(x))


def div_by_pot(x, constant_divisor_is_pot):
    return x >> log2(constant_divisor_is_pot)


def mul_by_pot(x, constant_multiplier_is_pot):
    return x << log2(constant_multiplier_is_pot)


def nMax(a, b):
    return Mux(a < b, a, b)


def nAny(seq):
    assert isinstance(seq, Iterable)
    return reduce(lambda a, b: a | b, seq)


def max_error_freq(real_freq, requested_freq, max_error_percent=1):
    freq_error = abs((1 - (real_freq / requested_freq)) * 100)
    if freq_error > max_error_percent:
        raise ValueError("the reqested freqency {}MHz cant be synthesized by the fclk with satisfying precision ("
                         "{}% error reqested; {}% error met) the real frequency would be {}MHz"
                         .format(requested_freq / 1e6, max_error_percent, freq_error,
                                 real_freq / 1e6))
    return freq_error


def delay_by(signal, cycles, m):
    delayed_signal = signal
    for i in range(cycles):
        last = delayed_signal
        if hasattr(signal, 'name'):
            name = "{}_delayed_{}".format(signal.name, i + 1)
        else:
            name = "expression_delayed_{}".format(i + 1)
        delayed_signal = Signal.like(signal, name=name)
        m.d.sync += delayed_signal.eq(last)
    return delayed_signal


def ends_with(signal, *patterns):
    return signal.matches(
        *(("-" * (len(signal) - len(pattern)) + pattern) for pattern in patterns)
    )


def connect_leds(m, platform, signal, upper_bits=True):
    for i in count(start=0, step=1):
        try:
            m.d.comb += platform.request("led", i).eq(signal[i if not upper_bits else -(i + 1)])
        except ResourceError:
            break
