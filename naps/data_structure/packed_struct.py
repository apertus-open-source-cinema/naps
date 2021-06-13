from typing import get_type_hints

from nmigen import *
from nmigen import tracer
from nmigen.hdl.ast import ValueCastable

from naps.util.python_misc import camel_to_snake

__all__ = ["packed_struct"]


class PackedStructBaseClass(ValueCastable):
    def __init__(self, backing_signal=None, name=None, src_loc_at=1, **kwargs):
        self.name = name or tracer.get_var_name(depth=2 + src_loc_at, default=camel_to_snake(self.__class__.__name__))

        if backing_signal is not None:
            if isinstance(backing_signal, Value):
                assert len(kwargs) == 0
                assert len(backing_signal) == self._PACKED_LEN
                self._backing_signal = backing_signal
            elif isinstance(backing_signal, int):
                from naps.soc.pydriver.hardware_proxy import BitwiseAccessibleInteger
                self._backing_signal = BitwiseAccessibleInteger(backing_signal)
            else:
                assert False, "unsupported type for backing signal"
        else:
            # we do not create a single backing signal but instead cat multiple signals together for better
            # introspection in the generated code and vcd files
            def get_signal(name, type):
                if name in kwargs:
                    signal = kwargs[name]
                    if hasattr(type, "_PACKED_FIELDS"):
                        assert isinstance(signal, type)
                    if isinstance(signal, ValueCastable):
                        signal = signal.as_value()
                    elif not isinstance(signal, Value):
                        signal = Const(signal, type)
                    assert needed_bits(type) == len(signal), f"field {name} of type {type} needs {needed_bits(type)} bits but got {len(signal)} bits"
                    signal.name = f'{self.name}__{name}'
                    return signal
                elif hasattr(type, "_PACKED_FIELDS"):
                    return type(name=f'{self.name}__{name}')
                else:
                    return Signal(type, name=f'{self.name}__{name}')

            self.backing_signals = {
                name: get_signal(name, type)
                for name, type in self._PACKED_FIELDS.items()
            }
            self._backing_signal = Cat(self.backing_signals.values())

    def __getattribute__(self, item):
        if item in object.__getattribute__(self, "_PACKED_FIELDS"):
            if hasattr(self, "backing_signals"):
                # we have the individual components of the signal so we do not need to slice them out
                return self.backing_signals[item]
            else:
                # fallback path for when we are backed by a single signal
                start, stop = self._PACKED_SLICES[item]
                type = self._PACKED_FIELDS[item]
                if hasattr(type, "_PACKED_FIELDS"):
                    return type(self._backing_signal[start:stop])
                else:
                    return self._backing_signal[start:stop]
        else:
            return object.__getattribute__(self, item)

    def __len__(self):
        return self._PACKED_LEN

    def fields(self):
        return list(self._PACKED_SLICES.keys())

    @ValueCastable.lowermethod
    def as_value(self):
        return self._backing_signal

    def eq(self, other):
        assert isinstance(other, self.__class__)
        return self.as_value().eq(other.as_value())


def needed_bits(obj):
    if hasattr(obj, "_PACKED_LEN"):
        return obj._PACKED_LEN
    else:
        return Shape.cast(obj).width


def packed_struct(cls):
    """A decorator that turns a class into a packed struct (similiar to dataclass)"""
    cls._PACKED_FIELDS = get_type_hints(cls)  # this only works in python 3.6+ because dict ordering is not consistent before
    cls._PACKED_SLICES = {}
    last_index = 0
    for name, field_type in cls._PACKED_FIELDS.items():
        bits = needed_bits(field_type)
        cls._PACKED_SLICES[name] = (last_index, last_index + bits)
        last_index += bits
    cls._PACKED_LEN = last_index

    return type(cls.__name__, (PackedStructBaseClass,), dict(cls.__dict__))
