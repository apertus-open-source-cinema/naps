from abc import ABC, abstractmethod
from textwrap import indent
from math import ceil, log2
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
            bit_mask = (2**(item.stop - item.start) - 1)
            return (self.value >> item.start) & bit_mask

    def __setitem__(self, key, value):
        if isinstance(key, int):
            assert key >= 0
            assert value <= 1, "you can at maximum assign '1' to a 1 bit value"
            self.value = self.value & (((2**ceil(log2(self.value + 1))) - 1) ^ (1 << key))
            self.value = self.value | ((value & 1) << key)
        elif isinstance(key, slice):
            assert (key.step == 1) or (key.step is None)
            assert 0 <= key.start <= key.stop
            bit_mask = (2**(key.stop - key.start) - 1)
            assert value <= bit_mask, "you can at maximum assign '{}' to a {} bit value".format(bit_mask, (key.stop - key.start))
            self.value = self.value & (((2 ** ceil(log2(self.value + 1))) - 1) ^ (bit_mask << key.start))
            self.value = self.value | ((value & bit_mask) << key.start)

    def __int__(self):
        return self.value


class HardwareProxy:
    # TODO: test bit fiddeling
    def __init__(self, memory_accessor: MemoryAccessor):
        object.__setattr__(self, "_memory_accessor", memory_accessor)
        for k, v in self.__class__.__dict__.items():
            if isinstance(v, type) and issubclass(v, HardwareProxy):
                object.__setattr__(self, k[1:].lower(), v(memory_accessor))

    def __getattribute__(self, name):
        if name.startswith("__"):
            return object.__getattribute__(self, name)

        if name in {**self.__dict__, **self.__class__.__dict__}:
            obj = object.__getattribute__(self, name)

            if not isinstance(obj, tuple):
                return obj
            else:
                addr, bit_start, bit_len = obj

                to_return = BitwiseAccessibleInteger()
                read_bytes = ceil((bit_start + bit_len) / 32)
                for i in range(read_bytes):
                    val = BitwiseAccessibleInteger(self._memory_accessor.read(addr - self._memory_accessor.base + (i * 4)))
                    to_return[i*32:(i+1)*32] = val[bit_start:32+bit_start - (0 if i != read_bytes - 1 else bit_len % 32)]
                return int(to_return)
        raise AttributeError("{} has no attribute {}".format(self.__class__.__name__, name))

    def __setattr__(self, name, value):
        if name.startswith("__"):
            return object.__setattr__(self, name, value)

        if name in self.__class__.__dict__:
            obj = object.__getattribute__(self, name)

            if not isinstance(obj, tuple):
                return obj
            else:
                addr, bit_start, bit_len = obj
                assert value < 2**bit_len,  "you can at maximum assign '{}' to a {} bit value".format((2**bit_len - 1), bit_len)
                v = BitwiseAccessibleInteger(value)
                read_bytes = ceil((bit_start + bit_len) / 32)
                for i in range(read_bytes):
                    prev_value = BitwiseAccessibleInteger(self._memory_accessor.read(addr - self._memory_accessor.base + (i * 4)))
                    prev_value[bit_start:32+bit_start - (0 if i != read_bytes - 1 else bit_len % 32)] = v[i * 32:(i + 1) * 32]
                    self._memory_accessor.write(
                        addr - self._memory_accessor.base + (i * 4),
                        int(prev_value)
                    )
        else:
            raise AttributeError("{} has no attribute {}".format(self.__class__.__name__, name))

    def __repr__(self, allow_recursive=False):
        if stack()[1].filename == "<console>" or allow_recursive:
            to_return = ""
            children = [(name, getattr(self, name)) for name in dir(self) if not name.startswith("_")]
            real_children = [(name, child) for name, child in children if not isinstance(child, HardwareProxy)]
            proxy_children = [(name, child) for name, child in children if isinstance(child, HardwareProxy)]
            for name, child in real_children:
                if callable(child):
                    to_return += "{}: method()\n".format(name)
                else:
                    to_return += "{}: {}\n".format(name, child)
            for name, child in proxy_children:
                to_return += "{}: \n{}\n".format(name, indent(child.__repr__(allow_recursive=True), "    "))
            return to_return.strip()
        else:
            return "<HardwareProxy at 0x{:x}>".format(id(self))
