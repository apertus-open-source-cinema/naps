from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar

from nmigen import *
from nmigen import tracer

from naps.util.python_misc import camel_to_snake

__all__ = ["Bundle", "Direction", "UPWARDS", "DOWNWARDS"]


class Bundle:
    def __init__(self, name=None, src_loc_at=1):
        super().__setattr__("name", name or tracer.get_var_name(depth=1 + src_loc_at, default="$" + camel_to_snake(self.__class__.__name__)))
        self._directions = OrderedDict()

    def __setattr__(self, key, value):
        if key == "name":
            super().__setattr__(key, value)
            self._update_name()

        if isinstance(value, Port):
            self._directions[key] = value.direction
            value = value.to_wrap
        elif isinstance(value, (Value, Bundle)):  # TODO: do we really want this behaviour also for values
            self._directions[key] = Direction.DOWNWARDS

        if hasattr(value, "name") and isinstance(value.name, str):
            if value.name.startswith("$"):  # with @UPWARDS and @DOWNWARDS we are breaking nmigens tracer
                value.name = key
            value.name = format("{}__{}".format(self.name, value.name))

        super().__setattr__(key, value)

    def __setitem__(self, key, value):
        assert isinstance(value, Port)
        self.__setattr__(key, value)

    def __getitem__(self, item):
        if item in self._directions:
            return getattr(self, item)
        else:
            raise KeyError(f"{item} not found in {repr(self)}")

    def _update_name(self):
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "name") and isinstance(attr.name, str):
                attr.name = format("{}__{}".format(self.name, attr.name.split("__")[-1]))

    def __repr__(self):
        return "<{}(Interface) name={}>".format(self.__class__.__name__, self.name)

    def connect_upstream(self, upstream, allow_partial=False, only=None, exclude=None):
        return self._connect(upstream, self, allow_partial, only, exclude)

    def connect_downstream(self, downstream, allow_partial=False, only=None, exclude=None):
        return self._connect(self, downstream, allow_partial, only, exclude)

    @property
    def signals(self):
        return [self[k] for k in self._directions.keys()]

    @staticmethod
    def _connect(upstream, downstream, allow_partial, only=None, exclude=None):
        if only is not None:
            assert exclude is None
            upstream_directions = {k: v for k, v in upstream._directions.items() if k in only}
            downstream_directions = {k: v for k, v in downstream._directions.items() if k in only}
        elif exclude is not None:
            assert only is None
            upstream_directions = {k: v for k, v in upstream._directions.items() if k not in exclude}
            downstream_directions = {k: v for k, v in downstream._directions.items() if k not in exclude}
        else:
            upstream_directions = upstream._directions
            downstream_directions = downstream._directions

        assert isinstance(upstream, Bundle) and isinstance(downstream, Bundle)
        if not allow_partial:
            assert upstream_directions == downstream_directions

        statements = []
        for k, direction in upstream_directions.items():
            if hasattr(upstream, k) and hasattr(downstream, k):
                assert upstream_directions[k] == downstream_directions[k]

                if direction == DOWNWARDS:
                    u, d = upstream[k], getattr(downstream, k)
                    if isinstance(d, Value):
                        statements += [d.eq(u)]
                    elif isinstance(d, Bundle):
                        statements += Bundle._connect(u, d, allow_partial)
                elif direction == UPWARDS:
                    u, d = upstream[k], downstream[k]
                    if isinstance(u, Value):
                        statements += [u.eq(d)]
                    elif isinstance(u, Bundle):
                        statements += Bundle._connect(d, u, allow_partial)
        return statements


class Direction(Enum):
    DOWNWARDS = 0
    UPWARDS = 1

    T = TypeVar('T')  # we lie about the return type to get nice IDE completions
    def __rmatmul__(self, other: T) -> T:
        return Port(self, other)


DOWNWARDS = Direction.DOWNWARDS
UPWARDS = Direction.UPWARDS


@dataclass
class Port:
    direction: Direction
    to_wrap: object
