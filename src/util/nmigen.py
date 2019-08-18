from nmigen import *


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
    signals_records = [prop for prop in [getattr(module, name) for name in dir(module) if name[0] != "_"] if is_nmigen_type(prop)]
    log(signals_records)
    return flatten_nmigen_type(signals_records)
