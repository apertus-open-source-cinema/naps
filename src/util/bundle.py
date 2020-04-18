from dataclasses import dataclass
from enum import Enum

from nmigen import *
from nmigen.hdl.ast import UserValue


@dataclass
class Bundle(UserValue):
    def __init__(self):
        super().__init__()

    def lower(self):
        nmigen_fields = [f for f in dir(self) if isinstance(getattr(self, f), (Value, int, Enum))]
        raise NotImplemented("lowering bundles is not supported at the moment")
        return Record()
