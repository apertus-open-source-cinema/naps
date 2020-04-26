from dataclasses import dataclass
from enum import Enum

from nmigen import *
from nmigen import tracer
from nmigen._utils import union
from nmigen.hdl.ast import UserValue, SignalSet


@dataclass
class Bundle(UserValue):
    def __init__(self, name=None, src_loc_at=1):
        super().__init__()
        self.name = name or tracer.get_var_name(depth=2 + src_loc_at, default="$bundle")

    def __setattr__(self, key, value):
        if hasattr(value, "name") and isinstance(value.name, str):
            value.name = format("{}__{}".format(self.name, value.name))
        if hasattr(value, "_update_name") and callable(value._update_name):
            value._update_name()
        super().__setattr__(key, value)

    def _update_name(self):
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "name") and isinstance(attr.name, str):
                attr.name = format("{}__{}".format(self.name, attr.name.split("__")[-1]))

    def __repr__(self):
        return "{}(name={})".format(self.__class__.__name__, self.name)

    def lower(self):
        raise NotImplemented("lowering bundles is not supported at the moment")

    def _nmigen_fields(self):
        return {f: getattr(self, f) for f in dir(self) if isinstance(getattr(self, f), Value)}

    def _lhs_signals(self):
        return union((f._lhs_signals() for f in self._nmigen_fields().values()), start=SignalSet())

    def _rhs_signals(self):
        return union((f._rhs_signals() for f in self._nmigen_fields().values()), start=SignalSet())