import math
from collections import defaultdict
from functools import reduce
import operator
from typing import Iterator

from nmigen import *
from nmigen.build import Clock


def flatten_nmigen_type(records):
    """Flattens a list of signals and records to a list of signals
    :param records: A list of signals and records
    :return: A list of signals
    """
    flattened = []
    for signal in records:
        if isinstance(signal, Signal):
            flattened.append(signal)
        elif isinstance(signal, Record):
            flattened = [*flattened, *flatten_nmigen_type(signal.fields.values())]
        elif isinstance(signal, list):
            flattened = [*flattened, *flatten_nmigen_type(signal)]
    return flattened


def is_nmigen_type(obj):
    """Checks, wether an object is a nmigen type or a list of these"""
    if isinstance(obj, Signal) or isinstance(obj, Record):
        return True
    elif isinstance(obj, list):
        return all([is_nmigen_type(elem) for elem in obj])


def get_signals(module):
    """Create a list of all signals of a module

    :param module: The module to investigate
    :return A list of property Signals
    """
    signals_records = [prop for prop in [getattr(module, name) for name in dir(module) if name[0] != "_"] if
                       is_nmigen_type(prop)]
    return flatten_nmigen_type(signals_records)


def generate_states(str_pattern, n, next_state):
    return ((i, str_pattern.format(i), str_pattern.format(i + 1) if i <= n else next_state) for i in range(n))


def connect_together(signal, name, internal_dict=defaultdict(list), operation=operator.or_):
    """
    This function can be used as a hack to connect multiple signals which are not all known at a single point of
    time with a logical or. This is e.g. useful when we want to connect busses in an ad-hoc way.
    :param operation: the logical operation which connects the signals. normally either | or &
    :param signal: The signal to add to the collection of or-ed Signals
    :param name: The name to which the current signal should be or-ed. Pay attention to create a really unique name here.
    :param internal_dict: DONT OVERWRITE THIS (internally used mapping of name to signals)
    :return: The 'oring' of signals with the same name until now
    """
    internal_dict[name].append(signal)
    return reduce(operation, internal_dict[name])


def iterator_with_if_elif(iterator: Iterator, module: Module) -> Iterator:
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


def max_error_freq(real_freq: Clock, requested_freq: Clock, max_error_percent=1):
    freq_error = abs((1 - (real_freq.frequency / requested_freq.frequency)) * 100)
    if freq_error > max_error_percent:
        raise ValueError("the reqested freqency {}MHz cant be synthesized by the fclk with satisfying precision ("
                         "{}% error reqested; {}% error met) the real frequency would be {}MHz"
                         .format(requested_freq.frequency / 1e6, max_error_percent, freq_error,
                                 real_freq.frequency / 1e6))
    return freq_error
