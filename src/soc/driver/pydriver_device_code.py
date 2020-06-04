import mmap
import os
import struct
from math import ceil


class DevMem:
    word = 4
    mask = ~(word - 1)

    def __init__(self, base_addr, bytes=None, filename='/dev/mem'):
        if bytes is None:
            bytes = mmap.PAGESIZE

        assert (base_addr % mmap.PAGESIZE) == 0

        bytes = int(ceil(bytes / mmap.PAGESIZE) * mmap.PAGESIZE)

        self.base = base_addr

        self.f = os.open(filename, os.O_RDWR | os.O_SYNC)
        self.mem = mmap.mmap(self.f, bytes, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=base_addr)

    def __del__(self):
        os.close(self.f)

    def read_int(self, offset):
        self.mem.seek(offset)
        return struct.unpack('I', self.mem.read(4))[0]

    def write_int(self, offset, din):
        self.mem.seek(offset)
        return self.mem.write(struct.pack('I', din))


devmem = DevMem(0x4000_0000)


class CSRApiWrapper:
    def __getattribute__(self, name):
        if name.startswith("__"):
            return object.__getattribute__(self, name)

        if name in self.__class__.__dict__:
            obj = object.__getattribute__(self, name)

            if not isinstance(obj, tuple):
                return obj
            else:
                addr, bit_start, bit_len = obj

                val = devmem.read_int(addr - devmem.base)
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

                return devmem.write_int(addr - devmem.base, value)
        raise AttributeError("{} has no attribute {}".format(self.__class__.__name__, name))
