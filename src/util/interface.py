from dataclasses import dataclass
from enum import Enum

from nmigen import *
from nmigen import tracer

from util.py_util import camel_to_snake


class Interface:
    def __init__(self, name=None, src_loc_at=1):
        self.name = name or tracer.get_var_name(depth=2 + src_loc_at, default=camel_to_snake(self.__class__.__name__))
        self._directions = {}

    def __setattr__(self, key, value):
        if isinstance(value, Port):
            self._directions[key] = value.direction
            value = value.to_wrap
        elif isinstance(value, (Value, Interface)):  # TODO: do we really want this behaviour also for values
            self._directions[key] = Direction.DOWN

        if hasattr(value, "name") and isinstance(value.name, str):
            if value.name == "$signal":  # with up() and down() we are breaking nmigens tracer
                value.name = key
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
        return "<{}(Interface) name={}>".format(self.__class__.__name__, self.name)

    def connect_upstream(self, upstream):
        return self._connect(upstream, self)

    def connect_downstream(self, downstream):
        return self._connect(self, downstream)

    @staticmethod
    def _connect(upstream, downstream):
        assert upstream._directions == downstream._directions
        statements = []

        for u, d, direction in [
            (getattr(upstream, k), getattr(downstream, k), upstream._directions[k])
            for k in upstream._directions.keys()
        ]:
            if direction == Direction.DOWN:
                if isinstance(d, Value):
                    statements += [d.eq(u)]
                elif isinstance(d, Interface):
                    statements += Interface._connect(u, d)
            else:
                if isinstance(u, Value):
                    statements += [u.eq(d)]
                elif isinstance(u, Interface):
                    statements += Interface._connect(d, u)

        return statements


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
