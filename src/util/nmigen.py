from collections import defaultdict
from contextlib import contextmanager
from functools import reduce
import operator
from typing import Iterator

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

def _opposed_direction(dir):
    return { "input": "output", "output": "input", "bidirectional": "bidirectional" }[dir]

def _dir_to_netlistsvg(dir):
    return { "i": "input", "o": "output", "io": "bidirectional" }[dir]

def _beautify_nmigen_name(s):
    return s.replace("__", "/")

def _hierarchy_to_dot_frag(frag: Fragment, hierarchy = ["top"], _bits = [0]):
    def next_bit():
        nonlocal _bits
        bit = _bits[0]
        _bits[0] += 1

        return bit

    from nmigen.hdl import ir

    cells = {}

    cell = {}
    cell["type"] = hierarchy[-1]
    cell["port_directions"] = {}
    cell["connections"] = {}

    ports = {}

    if isinstance(frag, ir.Instance):
        for name, (value, dir) in frag.named_ports.items():
            dir = _dir_to_netlistsvg(dir)

            ports[name] = {}
            ports[name]["direction"] = dir

            cell["port_directions"][name] = dir
            cell["connections"][name] = [next_bit() for _ in range(value.shape().width)]
    else:
        ports = {}

        for sig, dir in frag.ports.items():
            name =_beautify_nmigen_name(sig.name)
            dir = _dir_to_netlistsvg(dir)

            ports[name] = {}
            ports[name]["direction"] = dir
            cell["port_directions"][name] = dir
            cell["connections"][name] = [next_bit() for _ in range(sig.shape().width)]

        for (sub_frag, sub_name) in frag.subfragments:
            if sub_name == "instance":
                sub_name = hierarchy[-1] + "/" + sub_name

            new_cells, new_ports = _hierarchy_to_dot_frag(sub_frag, hierarchy + [sub_name])

            # print("hierarchy", hierarchy)
            # print("submod", sub_name)
            # print("my ports", ports)
            # print("new_ports", new_ports)
            # print("new_cells", new_cells)
            # print("cell[port_directions]", cell["port_directions"])


            # print(ports)

            for port_name, dir in new_ports.items():
                if port_name in cell["port_directions"]:
                    wrapped_port_name = sub_name + "/" + port_name
                else:
                    wrapped_port_name = port_name

                assert wrapped_port_name not in cell["port_directions"]

                dir = dir["direction"]
                cell["port_directions"][wrapped_port_name] = _opposed_direction(dir)
                cell["connections"][wrapped_port_name] = new_cells[sub_name]["connections"][port_name]

            for name, cell_ in new_cells.items():
                if name not in cells:
                    cells[name] = cell_
                else:
                    i = 1

                    while name in cells:
                        name = hierarchy[-i] + "/" + sub_name
                        i += 1

                    cells[name] = cell_

        # print(frag.named_ports)
        # print(frag.subfragments)


    cells[hierarchy[-1]] = cell

    return cells, ports

def hierarchy_to_dot(e: Elaboratable, plat = None, **kwargs):
    from nmigen.hdl import ir
    frag = ir.Fragment.get(e, plat).prepare(**kwargs)

    cells, toplevel_ports = _hierarchy_to_dot_frag(frag)

    for port_name in list(toplevel_ports.keys()):
        wrapped_port_name = port_name.replace(".", "/")

        if wrapped_port_name != port_name:
            toplevel_ports[wrapped_port_name] = toplevel_ports[port_name]
            del toplevel_ports[port_name]

        toplevel_ports[wrapped_port_name]["bits"] = cells["top"]["connections"][port_name]


    out = { "modules": { "top": { "cells": cells, "ports": toplevel_ports } } }

    import json
    return json.dumps(out, indent=4)
