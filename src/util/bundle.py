from dataclasses import dataclass
from enum import Enum

from nmigen import *
from nmigen import tracer
from nmigen.hdl.ast import UserValue


@dataclass
class Bundle(UserValue):
    def __init__(self, name=None, src_loc_at=1, parent_name=None):
        super().__init__()
        self.name = name or tracer.get_var_name(depth=2 + src_loc_at, default="$bundle")
        if parent_name:
            self.name = "{}__{}".format(parent_name, self.name)

    def Signal(self, *args, name=None, src_loc_at=0, **kwargs):
        name = name or tracer.get_var_name(depth=2 + src_loc_at, default="$signal")
        return Signal(name="{}__{}".format(self.name, name), src_loc_at=src_loc_at, *args, *kwargs)

    def lower(self):
        nmigen_fields = [f for f in dir(self) if isinstance(getattr(self, f), (Value, int, Enum))]
        raise NotImplemented("lowering bundles is not supported at the moment")
        return Record()
