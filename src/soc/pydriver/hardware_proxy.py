from abc import ABC, abstractmethod
from textwrap import indent


class MemoryAccessor(ABC):
    base = 0

    @abstractmethod
    def read(self, addr):
        raise NotImplementedError()

    @abstractmethod
    def write(self, addr, value):
        raise NotImplementedError()


class HardwareProxy:
    def __init__(self, memory_accessor: MemoryAccessor):
        object.__setattr__(self, "_memory_accessor", memory_accessor)
        for k, v in self.__class__.__dict__.items():
            if isinstance(v, type) and issubclass(v, HardwareProxy):
                object.__setattr__(self, k[1:].lower(), v(memory_accessor))

    def __getattribute__(self, name):
        if name.startswith("__") or name == "print_state":
            return object.__getattribute__(self, name)

        if name in {**self.__dict__, **self.__class__.__dict__}:
            obj = object.__getattribute__(self, name)

            if not isinstance(obj, tuple):
                return obj
            else:
                addr, bit_start, bit_len = obj

                val = self._memory_accessor.read(addr - self._memory_accessor.base)
                val = val >> bit_start

                return val & (0xffffffff >> (32 - bit_len))
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

                value = value & (0xffffffff >> (32 - bit_len))
                value = value << bit_start

                return self._memory_accessor.write(addr - self._memory_accessor.base, value)
        raise AttributeError("{} has no attribute {}".format(self.__class__.__name__, name))

    def print_state(self, indentation_level=-1, top_name=None):
        if top_name:
            print(indent("{}:".format(top_name), "    " * indentation_level))
        child_names = [name for name in dir(self) if not name.startswith("_") if name != "print_state"]
        for child_name in child_names:
            child = getattr(self, child_name)
            if isinstance(child, HardwareProxy):
                child.print_state(indentation_level + 1, top_name=child_name)
            else:
                print(indent("{}: {}".format(child_name, child), "    " * (indentation_level + 1)))
