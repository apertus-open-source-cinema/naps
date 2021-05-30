from types import MethodType

from nmigen import *
from nmigen.compat import Module as CompatModule
from nmigen.hdl.xfrm import TransformedElaboratable


class ElaboratableSames:
    def __init__(self):
        self.sames = []

    def insert(self, a, b):
        for row in self.sames:
            if a in row and b not in row:
                row.append(b)
                return
            elif b in row and a not in row:
                row.append(a)
                return
            elif b in row and a in row:
                return
        self.sames.append([a, b])

    def get_row(self, something):
        candidates = list(row for row in self.sames if something in row)
        if len(candidates) == 0:
            raise AssertionError()
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


def inject_elaborate_wrapper(obj, sames):
    if hasattr(obj, 'elaborate') and not isinstance(obj, Fragment):

        def generate_elaborate_wrapper(real_elaborate):
            def elaborate_wrapper(self, platform):
                elaborated = real_elaborate(platform)
                # print("{} ({}) elaborated to {} ({})".format(
                #     self.__class__.__name__, self,
                #     elaborated.__class__.__name__, elaborated
                # ))
                sames.insert(self, elaborated)
                inject_elaborate_wrapper(elaborated, sames)
                return elaborated
            return elaborate_wrapper

        obj.elaborate = MethodType(generate_elaborate_wrapper(obj.elaborate), obj)
    else:
        if not isinstance(obj, (Instance, Fragment)):
            raise AssertionError()

    if isinstance(obj, Module):
        submodules = [*obj._named_submodules.values(), *obj._anon_submodules]
        for elab in submodules:
            inject_elaborate_wrapper(elab, sames)
    elif isinstance(obj, CompatModule):
        submodules = [submod for name, submod in obj.submodules._cm._submodules]
        for elab in submodules:
            inject_elaborate_wrapper(elab, sames)
    elif isinstance(obj, TransformedElaboratable):
        inject_elaborate_wrapper(obj._elaboratable_, sames)
        for i in range(len(obj._transforms_)):

            def generate_transform_wrapper(real_transform):
                if hasattr(real_transform, "wrapped"):
                    real_transform = real_transform.wrapped

                def transform_wrapper(self, value, *, src_loc_at=0):
                    output = real_transform(self, value, src_loc_at=src_loc_at)
                    sames.insert(value, output)
                    # print("{} ({}) transformed to {} ({})".format(
                    #     value.__class__.__name__, value,
                    #     output.__class__.__name__, output
                    # ))
                    return output
                transform_wrapper.wrapped = real_transform
                return transform_wrapper

            obj._transforms_[i].__class__.__call__ = generate_transform_wrapper(obj._transforms_[i].__class__.__call__)
        sames.insert(obj, obj._elaboratable_)
    else:
        if not (isinstance(obj, (Fragment, Instance)) or hasattr(obj, 'elaborate')):
            raise AssertionError()


def fragment_get_with_elaboratable_trace(elaboratable, platform, sames=None):
    # this is a hack to retrieve the elaboratable which produced a specific module
    if sames is None:
        sames = ElaboratableSames()

    inject_elaborate_wrapper(elaboratable, sames)
    fragment = Fragment.get(elaboratable, platform)

    return fragment, sames
