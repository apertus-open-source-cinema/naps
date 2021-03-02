from nmigen import *


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
            cell["connections"][name] = [next_bit() for _ in range(value._shape().width)]
    else:
        ports = {}

        for sig, dir in frag.ports.items():
            name =_beautify_nmigen_name(sig.name)
            dir = _dir_to_netlistsvg(dir)

            ports[name] = {}
            ports[name]["direction"] = dir
            cell["port_directions"][name] = dir
            cell["connections"][name] = [next_bit() for _ in range(sig._shape().width)]

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
    frag = ir.Fragment.get(e, plat).prepare()

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