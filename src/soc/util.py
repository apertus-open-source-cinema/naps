from textwrap import indent
from typing import Dict, Iterable

from nmigen import *
from nmigen.hdl.xfrm import TransformedElaboratable


def fragment_get_with_elaboratable_trace(elaboratable, platform):
    # this is a hack to retrieve the elaboratable which produced a specific module
    elaboratables = {}

    def inject_elaborate_wrapper(elaboratable, level=0, text_prefix=""):
        if isinstance(elaboratable, TransformedElaboratable):
            elaboratable = elaboratable._elaboratable_
        real_elaborate = elaboratable.elaborate

        def elaborate_wrapper(platform):
            print(indent("{}elaborating {!r}".format(text_prefix, elaboratable), "    " * level))

            obj = real_elaborate(platform)
            elaboratables[elaboratable] = obj

            if isinstance(obj, Module):
                submodules = [*obj._named_submodules.values(), *obj._anon_submodules]
                for elab in submodules:
                    inject_elaborate_wrapper(elab, level + 1, text_prefix="s> ")
            inject_elaborate_wrapper(obj, level + 1, text_prefix="e> ")

            return obj

        elaboratable.elaborate = elaborate_wrapper

    inject_elaborate_wrapper(elaboratable)
    fragment = Fragment.get(elaboratable, platform)

    return fragment, elaboratables


def flatten(list):
    flat = []
    for item in list:
        if isinstance(item, Iterable):
            flat += flatten(item)
        else:
            flat += [item]
    return flat


def find_elaboratable_sames(elaboratable_trace: Dict, top=None):
    if top is None:
        children = [
            [key, *flatten(find_elaboratable_sames(elaboratable_trace, value))]
            for key, value in elaboratable_trace.items() if key not in elaboratable_trace.values()
        ]
    else:
        children = [
            [key, *find_elaboratable_sames(elaboratable_trace, value)]
            for key, value in elaboratable_trace.items() if key == top
        ]
    return children if children else [top]
