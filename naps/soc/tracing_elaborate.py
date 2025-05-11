from types import MethodType

from amaranth import *


def get_elaboratable(frag: Fragment):
    if isinstance(frag, Instance):
        return None
    else:
        try:
            return (o for o in frag.origins
                        if isinstance(o, Elaboratable)
                        and not isinstance(o, Module))
        except:
            print(f"no elaboratable found for {frag}")
            return None


def get_module(frag: Fragment):
    if isinstance(frag, Instance):
        return None
    else:
        try:
            return next(o for o in frag.origins if isinstance(o, Module))
        except StopIteration:
            print(f"no module found for {frag}")
            return None
