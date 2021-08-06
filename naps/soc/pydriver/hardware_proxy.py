from abc import ABC, abstractmethod
from dataclasses import dataclass
from textwrap import indent
from math import ceil
from inspect import stack


class MemoryAccessor(ABC):
    base = 0

    @abstractmethod
    def read(self, addr):
        raise NotImplementedError()

    @abstractmethod
    def write(self, addr, value):
        raise NotImplementedError()


class BitwiseAccessibleInteger:
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
            self.value = self.value & (((1 << (self.value + 1).bit_length()) - 1) ^ (1 << key))
            self.value = self.value | ((value & 1) << key)
        elif isinstance(key, slice):
            assert (key.step == 1) or (key.step is None)
            assert 0 <= key.start <= key.stop
            slice_length = key.stop - key.start
            bit_mask = ((1 << slice_length) - 1)
            assert value <= bit_mask, "you can at maximum assign '{}' to a {} bit value".format(bit_mask, (key.stop - key.start))
            self.value = self.value & (((1 << (self.value + 1).bit_length()) - 1) ^ (bit_mask << key.start))
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
    writable: bool
    readable: bool
    bit_mask: int = None
    word_aligned_inverse_bit_mask: int = None

    def __post_init__(self):
        self.bit_mask = (2**self.bit_len - 1) << self.bit_start
        num_words = (self.bit_start + self.bit_len + 31) // 32
        self.word_aligned_inverse_bit_mask = (2**(num_words * 32) - 1) ^ self.bit_mask


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

            assert obj.readable, f"cannot read write-only value {name}"
            # fast path if the value is easy to handle
            if obj.bit_start == 0 and obj.bit_len <= 32:
                return memory_accessor.read(obj.address - memory_accessor.base) & obj.bit_mask

            to_return = BitwiseAccessibleInteger()
            read_bytes = ceil((obj.bit_start + obj.bit_len) / 32)
            for i in range(read_bytes):
                val = BitwiseAccessibleInteger(memory_accessor.read(obj.address - memory_accessor.base + (i * 4)))
                to_return[i * 32:(i + 1) * 32] = val[obj.bit_start if i == 0 else 0:(32 if i != read_bytes - 1 else (obj.bit_len + obj.bit_start) % 32)]
            to_return = int(to_return)
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
                assert obj.writable, f"cannot write read-only value {name}"

                memory_accessor = object.__getattribute__(self, "_memory_accessor")
                assert value < 2 ** obj.bit_len, "you can at maximum assign '{}' to a {} bit value".format((2 ** obj.bit_len - 1), obj.bit_len)
            
                # fast path if the value is easy to handle
                if obj.bit_start == 0 and obj.bit_len <= 32:
                    old = memory_accessor.read(obj.address - memory_accessor.base)
                    memory_accessor.write(obj.address - memory_accessor.base, old & obj.word_aligned_inverse_bit_mask | value)
                    return

                v = BitwiseAccessibleInteger(value)
                read_bytes = ceil((obj.bit_start + obj.bit_len) / 32)
                for i in range(read_bytes):
                    prev_value = BitwiseAccessibleInteger(memory_accessor.read(obj.address - memory_accessor.base + (i * 4)))
                    prev_value[obj.bit_start if i == 0 else 0:(32 if i != read_bytes - 1 else (obj.bit_len + obj.bit_start) % 32)] = v[i * 32:(i + 1) * 32]
                    memory_accessor.write(
                        obj.address - memory_accessor.base + (i * 4),
                        int(prev_value)
                    )

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
