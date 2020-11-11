from dataclasses import dataclass

from nmigen import *
from nmigen import tracer
from nmigen.hdl.ast import ValueCastable

from util.py_util import camel_to_snake


@dataclass
class PackedStruct(ValueCastable):
    def __init__(self, name=None, src_loc_at=1):
        super().__init__()
        self._order = []
        self.name = name or tracer.get_var_name(depth=2 + src_loc_at, default=camel_to_snake(self.__class__.__name__))

    def __setattr__(self, key, value):
        if hasattr(value, "name") and isinstance(value.name, str):
            value.name = format("{}__{}".format(self.name, value.name))
        if hasattr(value, "_update_name") and callable(value._update_name):
            value._update_name()
        if isinstance(value, (Value, ValueCastable)):
            self._order.append(value)
        super().__setattr__(key, value)

    def _update_name(self):
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "name") and isinstance(attr.name, str):
                attr.name = format("{}__{}".format(self.name, attr.name.split("__")[-1]))

    def __repr__(self):
        return "{}(name={})".format(self.__class__.__name__, self.name)

    def eq(self, other):
        return self.as_value().eq(other)

    @ValueCastable.lowermethod
    def as_value(self):
        return Cat(self._order)
