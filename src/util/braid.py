from dataclasses import dataclass
from enum import Enum

from nmigen import *
from nmigen import tracer

from util.py_util import camel_to_snake


class Direction(Enum):
    DOWN = 0
    UP = 1


@dataclass
class Port:
    direction: Direction
    to_wrap: object


def up(to_wrap):
    return Port(to_wrap=to_wrap, direction=Direction.UP)


def down(to_wrap):
    return Port(to_wrap=to_wrap, direction=Direction.DOWN)


class Braid:
    def __init__(self, name=None, src_loc_at=1):
        self.name = name or tracer.get_var_name(depth=2 + src_loc_at, default=camel_to_snake(self.__class__.__name__))
        self._directions = {}

    def __setattr__(self, key, value):
        if isinstance(value, Port):
            self._directions[key] = value.direction
            value = value.to_wrap

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
        return "<{}(Braid) name={}>".format(self.__class__.__name__, self.name)

    def connect_upstream(self, upstream):
        return self._connect(upstream, self)

    def connect_downstream(self, downstream):
        return self._connect(self, downstream)

    @staticmethod
    def _connect(upstream, downstream):
        assert upstream._directions == downstream._directions
        statements = []
        downstream_attrs = [getattr(downstream, k) for k in downstream._directions.keys()]
        upstream_attrs = [getattr(upstream, k) for k in upstream._directions.keys()]
        for direction, u, d in zip(upstream_attrs, downstream_attrs, upstream._directions):
            if direction == Direction.DOWN:
                if isinstance(d, Value):
                    statements += [d.eq(u)]
            else:
                if isinstance(d, Value):
                    statements += [d.eq(u)]
