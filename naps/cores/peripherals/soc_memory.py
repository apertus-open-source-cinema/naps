from nmigen import *
from naps.soc import SocPlatform, MemoryMap, Peripheral, Response, driver_method

__all__ = ["SocMemory"]

from naps.util.past import Rose


class SocMemory(Elaboratable):
    """A memory that can be read / written to by the soc"""

    def __init__(self, *, width, depth, init=None, name=None, soc_read=True, soc_write=True, **kwargs):
        self.memory = Memory(width=width, depth=depth, init=init, name=name, **kwargs)
        self.soc_read = soc_read
        self.soc_write = soc_write
        self.depth = depth


    def handle_read(self, m, addr, data, read_done):
        if self.soc_read:
            read_port = self.memory.read_port(domain="sync", transparent=False)
            m.submodules += read_port
            with m.If(addr > self.depth - 1):
                read_done(Response.ERR)
            with m.Else():
                is_read = Signal()
                m.d.comb += is_read.eq(1)
                with m.If(Rose(m, is_read)):
                    m.d.comb += read_port.addr.eq(addr)
                with m.Else():
                    m.d.sync += data.eq(read_port.data)
                    read_done(Response.OK)
        else:
            read_done(Response.ERR)

    def handle_write(self, m, addr, data, write_done):
        if self.soc_write:
            write_port = self.memory.write_port(domain="sync")
            m.submodules += write_port
            with m.If(addr > self.depth - 1):
                write_done(Response.ERR)
            with m.Else():
                m.d.comb += write_port.addr.eq(addr)
                m.d.comb += write_port.data.eq(data)
                m.d.comb += write_port.en.eq(1)
                write_done(Response.OK)

        else:
            write_done(Response.ERR)

    def elaborate(self, platform):
        m = Module()

        if not isinstance(platform, SocPlatform):
            return m

        memorymap = MemoryMap()
        memorymap.allocate("memory", writable=True, bits=self.depth * memorymap.bus_word_width)
        m.submodules += Peripheral(
            self.handle_read,
            self.handle_write,
            memorymap
        )

        return m

    def read_port(self, *args, **kwargs):
        return self.memory.read_port(*args, **kwargs)

    def write_port(self, *args, **kwargs):
        return self.memory.write_port(*args, **kwargs)

    @driver_method
    def __getitem__(self, item):
        return self._memory_accessor.read(self.memory.address + item)

    @driver_method
    def __setitem__(self, item, value):
        self._memory_accessor.write(self.memory.address + item, value)
