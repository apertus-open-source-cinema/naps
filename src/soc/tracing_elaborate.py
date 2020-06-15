from textwrap import indent

from nmigen import *
from nmigen.compat import Module as CompatModule
from nmigen.hdl.xfrm import TransformedElaboratable


class ElaboratableSames:
    def __init__(self):
        self.sames = []

    def insert(self, a, b):
        for row in self.sames:
            if a in row:
                if b not in row:
                    row.append(b)
                return
            if b in row:
                if a not in row:
                    row.append(a)
                return
        self.sames.append([a, b])

    def get_row(self, something):
        candidates = list(row for row in self.sames if something in row)
        if len(candidates) == 0:
            return None
        if len(candidates) != 1:
            raise AssertionError()
        return candidates[0]

    def get_by_filter(self, something, item_filter):
        if isinstance(something, Instance):
            return None
        if self.get_row(something) is None:
            return None
        candidates = list(item for item in self.get_row(something) if item_filter(item))
        if len(candidates) == 0:
            return None
        if len(candidates) > 1:
            raise AssertionError()
        return candidates[0]

    def get_module(self, something):
        return self.get_by_filter(something, lambda x: isinstance(x, Module))

    def get_elaboratable(self, something):
        return self.get_by_filter(
            something, lambda x: isinstance(x, Elaboratable)
                                 and not isinstance(x, Module)
                                 and not isinstance(x, TransformedElaboratable)
        )


def fragment_get_with_elaboratable_trace(elaboratable, platform, sames=None):
    # this is a hack to retrieve the elaboratable which produced a specific module
    if sames is None:
        sames = ElaboratableSames()

    def inject_elaborate_wrapper(elaboratable, level=0, text_prefix=""):
        if isinstance(elaboratable, Module):
            submodules = [*elaboratable._named_submodules.values(), *elaboratable._anon_submodules]
            for elab in submodules:
                inject_elaborate_wrapper(elab, level + 1, text_prefix="\ns> ")
        elif isinstance(elaboratable, CompatModule):
            submodules = [submod for name, submod in elaboratable.submodules._cm._submodules]
            for elab in submodules:
                inject_elaborate_wrapper(elab, level + 1, text_prefix="\ncs> ")
        elif isinstance(elaboratable, TransformedElaboratable):
            inject_elaborate_wrapper(elaboratable._elaboratable_, level=0, text_prefix="\t\tx> ")
            sames.insert(elaboratable, elaboratable._elaboratable_)
        else:
            if not isinstance(elaboratable, (Fragment, Instance, Elaboratable)):
                raise AssertionError()

        if hasattr(elaboratable, 'elaborate'):
            real_elaborate = elaboratable.elaborate

            def elaborate_wrapper(platform):
                print(indent("{}elaborating {} ".format(text_prefix, elaboratable.__class__.__name__), "    " * level),
                      end="")
                obj = real_elaborate(platform)
                sames.insert(elaboratable, obj)

                inject_elaborate_wrapper(obj, 0, text_prefix="\t\te> ")
                return obj

            elaboratable.elaborate = elaborate_wrapper

    # top level
    inject_elaborate_wrapper(elaboratable)
    fragment = Fragment.get(elaboratable, platform)

    return fragment, sames
