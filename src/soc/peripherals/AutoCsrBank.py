from nmigen import *

from soc import Response
from soc import MemoryMapFactory
from util.nmigen import iterator_with_if_elif


class AutoCsrBank(Elaboratable):
    def __init__(self):
        self._memory_map = MemoryMapFactory.MemoryMap()
        self._signals = {}

        self.m = Module()

    def reg(self, name, width=32, writable=True, reset=0):
        assert width <= self._memory_map.data_width
        assert name not in self._signals
        reg = Signal(width, reset=reset, name=name)
        self._signals[name] = (reg, writable)
        self._memory_map.add_resource(name, size=1)

        return reg

    def elaborate(self, platform):
        m = self.m

        def handle_read(m, addr, data, read_done):
            for conditional, (name, (start, end)) in iterator_with_if_elif(self._memory_map.resources(), m):
                reg, writable = self._signals[name]
                with conditional(addr == start):
                    m.d.sync += data.eq(reg)
                    read_done(Response.OK)
            with m.Else():
                read_done(Response.ERR)

        def handle_write(m, addr, data, write_done):
            for conditional, (name, (start, end)) in iterator_with_if_elif(self._memory_map.resources(), m):
                reg, writable = self._signals[name]
                with conditional(addr == start):
                    if writable:
                        m.d.sync += reg.eq(data)
                    write_done(Response.OK)
            with m.Else():
                write_done(Response.ERR)

        m.submodules += platform.BusSlave(
            handle_read=handle_read,
            handle_write=handle_write,
            memorymap=self._memory_map
        )

        return m
