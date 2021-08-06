from abc import ABC, abstractmethod
from dataclasses import dataclass
from textwrap import indent
from math import ceil, log2
from inspect import stack


class MemoryAccessor(ABC):
    base = 0

    @abstractmethod
    def read(self, addr, len):
        raise NotImplementedError()

    @abstractmethod
    def write(self, addr, value):
        raise NotImplementedError()


class BitwiseAccessibleInteger:
    @staticmethod
    def from_list(*args):
        pass

    def __init__(self, value=0):
        self.value = value

    def __getitem__(self, item):
        if isinstance(item, int):
            assert item >= 0
            return (self.value >> item) & 1
        elif isinstance(item, slice):
            assert 0 <= item.start <= item.stop
            assert (item.step == 1) or (item.step is None)
            bit_mask = (2 ** (item.stop - item.start) - 1)
            return (self.value >> item.start) & bit_mask

    def __setitem__(self, key, value):
        if isinstance(key, int):
            assert key >= 0
            assert value <= 1, "you can at maximum assign '1' to a 1 bit value"
            self.value = self.value & (((2 ** ceil(log2(self.value + 1))) - 1) ^ (1 << key))
            self.value = self.value | ((value & 1) << key)
        elif isinstance(key, slice):
            assert (key.step == 1) or (key.step is None)
            assert 0 <= key.start <= key.stop
            bit_mask = (2 ** (key.stop - key.start) - 1)
            assert value <= bit_mask, "you can at maximum assign '{}' to a {} bit value".format(bit_mask, (key.stop - key.start))
            self.value = self.value & (((2 ** ceil(log2(self.value + 1))) - 1) ^ (bit_mask << key.start))
            self.value = self.value | ((value & bit_mask) << key.start)

    def __int__(self):
        return self.value


@dataclass
class Value:
    """Represents a Value that is automatically converted to / from an Integer"""
    address: int
    bit_start: int
    bit_len: int
    decoder: dict
    bit_mask: int = None
    byte_aligned_bit_mask: int = None
    num_bytes: int = None
    max_value: int = None

    def __post_init__(self):
        self.num_bytes = (((self.bit_start + self.bit_len + 7) // 8 + 3) // 4) * 4
        self.bit_mask = (2**self.bit_len - 1) << self.bit_start
        self.byte_aligned_bit_mask = (2**(self.bit_len + self.bit_start) - 1) ^ self.bit_mask
        self.max_value = (2**self.bit_len - 1)


@dataclass
class Blob:
    """Represents bigger address chunks that are not useful to express as BitwiseAccessibleInteger"""
    address: int
    bit_start: int
    bit_len: int


class HardwareProxy:
    # TODO: test bit fiddeling
    def __init__(self, memory_accessor: MemoryAccessor):
        object.__setattr__(self, "_memory_accessor", memory_accessor)
        for k, v in self.__class__.__dict__.items():
            if isinstance(v, type) and issubclass(v, HardwareProxy):
                object.__setattr__(self, k[1:].lower(), v(memory_accessor))
        if hasattr(self, 'init_function'):
            self.init_function()

    def __getattribute__(self, name):
        obj = object.__getattribute__(self, name)

        if isinstance(obj, Value):
            memory_accessor = object.__getattribute__(self, "_memory_accessor")

            by = memory_accessor.read(obj.address - memory_accessor.base, obj.num_bytes)
            to_return = (int.from_bytes(by, "little") >> obj.bit_start) & obj.bit_mask
            if obj.decoder is not None:
                to_return = obj.decoder[to_return]
            return to_return
        else:
            return obj

    def __setattr__(self, name, value):
        if name.startswith("__"):
            return object.__setattr__(self, name, value)
        else:
            obj = object.__getattribute__(self, name)

            if not isinstance(obj, (Value, Blob)):
                return object.__setattr__(self, name, value)
            elif isinstance(obj, Value):
                memory_accessor = object.__getattribute__(self, "_memory_accessor")
                assert value <= obj.max_value, "you can at maximum assign '{}' to a {} bit value".format(obj.max_value, obj.bit_len)

                old_value = int.from_bytes(memory_accessor.read(obj.address - memory_accessor.base, obj.num_bytes), "little")
                masked = old_value & obj.byte_aligned_bit_mask
                new_value = masked & (value << obj.bit_start)
                memory_accessor.write(obj.address - memory_accessor.base, int.to_bytes(obj.num_bytes, "little"))

    def __repr__(self, allow_recursive=False):
        if stack()[1].filename == "<console>" or allow_recursive:
            to_return = ""
            children = [(name, object.__getattribute__(self, name)) for name in dir(self) if not name.startswith("_")]
            real_children = [(name, child) for name, child in children if not isinstance(child, HardwareProxy)]
            proxy_children = [(name, child) for name, child in children if isinstance(child, HardwareProxy)]
            for name, child in real_children:
                if type(child) == Value:
                    to_return += "{}: {}\n".format(name, getattr(self, name))
                if type(getattr(self.__class__, name, None)) == property:
                    to_return += "{}: {}\n".format(name, getattr(self, name))
            for name, child in proxy_children:
                to_return += "{}: \n{}\n".format(name, indent(child.__repr__(allow_recursive=True), "    "))
            return to_return.strip()
        else:
            return "<HardwareProxy at 0x{:x}>".format(id(self))
