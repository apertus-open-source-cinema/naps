from math import ceil
from amaranth import *
from amaranth.lib.memory import Memory

from naps import iterator_with_if_elif
from naps.soc import SocPlatform, MemoryMap, Peripheral, Response, driver_method, PERIPHERAL_DOMAIN

__all__ = ["SocMemory"]

from naps.util.past import Rose


class SocMemory(Elaboratable):
    """A memory that can be read / written to by the soc"""

    def __init__(self, data=None, *, shape=None, depth=None, init=None, soc_read=True, soc_write=True, **kwargs):
        self.memory = Memory(data, shape=shape, depth=depth, init=init, **kwargs)
        width = Shape.cast(self.memory.shape).width
        if soc_read:
            self.read_port = self.memory.read_port(domain=PERIPHERAL_DOMAIN)
        if soc_write:
            self.write_port = self.memory.write_port(domain=PERIPHERAL_DOMAIN, granularity=min(width, 32))
        self.soc_read = soc_read
        self.soc_write = soc_write
        self.depth = self.memory.depth
        self.shape = self.memory.shape
        self.split_stages = int(ceil(width / 32))

    def handle_read(self, m, addr, data, read_done):
        addr = addr[2:]
        if self.soc_read:
            with m.If(addr > (self.depth * self.split_stages) - 1):
                read_done(Response.ERR)
            with m.Else():
                is_read = Signal()
                m.d.comb += is_read.eq(1)
                with m.If(Rose(m, is_read)):
                    m.d.comb += self.read_port.addr.eq(addr // self.split_stages)
                with m.Else():
                    for cond, i in iterator_with_if_elif(range(self.split_stages), m):
                        with cond(((addr % self.split_stages) == i) if self.split_stages != 1 else True):  # yosys seems to be unable to optimize n % 1 == 0 to 1
                            m.d.sync += data.eq(self.read_port.data[32 * i:])
                    read_done(Response.OK)
        else:
            read_done(Response.ERR)

    def handle_write(self, m, addr, data, write_done):
        addr = addr[2:]
        if self.soc_write:
            with m.If(addr > (self.depth * self.split_stages) - 1):
                write_done(Response.ERR)
            with m.Else():
                m.d.comb += self.write_port.addr.eq(addr // self.split_stages)
                for cond, i in iterator_with_if_elif(range(self.split_stages), m):
                    with cond(((addr % self.split_stages) == i) if self.split_stages != 1 else True):  # yosys seems to be unable to optimize n % 1 == 0 to 1
                        m.d.comb += self.write_port.data.eq(data << (i * 32))
                        m.d.comb += self.write_port.en.eq(1 << i)
                write_done(Response.OK)

        else:
            write_done(Response.ERR)

    def elaborate(self, platform):
        if not isinstance(platform, SocPlatform):
            return self.memory

        m = Module()
        memorymap = MemoryMap()
        assert memorymap.bus_word_width == 32
        memorymap.allocate("memory", writable=True, bits=self.depth * self.split_stages * memorymap.bus_word_width)
        m.submodules += Peripheral(
            self.handle_read,
            self.handle_write,
            memorymap
        )
        m.submodules.backing = self.memory

        return m

    def read_port(self, *args, **kwargs):
        return self.memory.read_port(*args, **kwargs)
    
    def write_port(self, *args, **kwargs):
        return self.memory.write_port(*args, **kwargs)

    @driver_method
    def __getitem__(self, item):
        base_address = self.memory.address - self._memory_accessor.base + 4*item * self.split_stages
        value = 0
        for i in range(self.split_stages):
            read = self._memory_accessor.read(base_address + 4*i)
            value |= read << (32 * i)
        return value

    @driver_method
    def __setitem__(self, item, value):
        base_address = self.memory.address - self._memory_accessor.base + 4*item * self.split_stages
        for i in range(self.split_stages):
            write = (value >> (32 * i)) & 0xFFFFFFFF
            self._memory_accessor.write(base_address + 4*i, write)
