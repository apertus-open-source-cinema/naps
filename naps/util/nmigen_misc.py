import math
from functools import reduce
from itertools import count
from typing import Iterator, Iterable

from nmigen import *
from nmigen import Mux
from nmigen.build import ResourceError

__all__ = ["iterator_with_if_elif", "assert_is_pot", "log2", "nMin", "nMax", "nAny", "nAll",
           "max_error_freq", "delay_by", "ends_with", "connect_leds", "with_reset", "nAvrg",
           "nAbsDifference", "fake_differential"]


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


def assert_is_pot(x):
    assert int(math.log2(x)) == math.log2(x), "{} is not a power of two".format(x)


def log2(x):
    assert_is_pot(x)
    return int(math.log2(x))


def nMin(a, b):
    return Mux(a < b, a, b)


def nMax(a, b):
    return Mux(a > b, a, b)


def nAny(seq):
    assert isinstance(seq, Iterable)
    return reduce(lambda a, b: a | b, seq)


def nAll(seq):
    assert isinstance(seq, Iterable)
    return reduce(lambda a, b: a & b, seq)


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
        *((("-" * (len(signal) - len(pattern))) + pattern) for pattern in patterns)
    )


def connect_leds(m, platform, signal, upper_bits=True):
    for i in count(start=0, step=1):
        try:
            m.d.comb += platform.request("led", i).eq(signal[i if not upper_bits else -(i + 1)])
        except ResourceError:
            break


def with_reset(m, signal, exclusive=False):
    domain_name = "with_reset_{}".format(signal.name)
    m.domains += ClockDomain(domain_name)
    m.d.comb += ClockSignal(domain_name).eq(ClockSignal())
    if not exclusive:
        m.d.comb += ResetSignal(domain_name).eq(ResetSignal() | signal)
    else:
        m.d.comb += ResetSignal(domain_name).eq(signal)
    return DomainRenamer(domain_name)


def nAvrg(*values):
    return sum(values) // len(values)


def nAbsDifference(a, b):
    return Mux(a > b, a - b, b - a)


def fake_differential(v):
    return Mux(v, 0b01, 0b10)