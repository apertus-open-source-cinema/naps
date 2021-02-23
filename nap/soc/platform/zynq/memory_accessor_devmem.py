import mmap
import os
import struct
from math import ceil


class DevMemAccessor:
    word = 4
    mask = ~(word - 1)

    def __init__(self, base_addr=0x4000_0000, bytes=None, filename='/dev/mem'):
        if bytes is None:
            bytes = mmap.PAGESIZE

        assert (base_addr % mmap.PAGESIZE) == 0

        bytes = int(ceil(bytes / mmap.PAGESIZE) * mmap.PAGESIZE)

        self.base = base_addr

        self.f = os.open(filename, os.O_RDWR | os.O_SYNC)
        self.mem = mmap.mmap(self.f, bytes, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=base_addr)

    def __del__(self):
        os.close(self.f)

    def read(self, offset):
        self.mem.seek(offset)
        return struct.unpack('I', self.mem.read(4))[0]

    def write(self, offset, to_write):
        self.mem.seek(offset)
        return self.mem.write(struct.pack('I', to_write))


MemoryAccessor = DevMemAccessor
