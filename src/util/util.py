from nmigen import *


def flatten_records(records):
    """Flattens a list of signals and records to a list of signals
    :param records: A list of signals and records
    :return: A list of signals
    """
    flattened = []
    for signal in records:
        if isinstance(signal, Signal):
            flattened.append(signal)
        if isinstance(signal, Record):
            flattened = [*flattened, *flatten_records(signal.fields.values())]
    return flattened
