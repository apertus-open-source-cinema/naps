from nmigen import *

from soc import Response
from soc import MemoryMapFactory
from soc.SocPlatform import SocPlatform


class SocRegister(Elaboratable):
    def __init__(self, *, width, name, writable=True, reset=0):
        self.name = name
        self.reg = Signal(width, name="{}_reg".format(name), reset=reset)
        self.writable = writable

    def elaborate(self, platform: SocPlatform):
        m = Module()

        def handle_read(m, addr, data, read_done):
            m.d.sync += data.eq(self.reg)
            read_done(Response.OK)

        def handle_write(m, addr, data, write_done):
            if self.writable:
                m.d.sync += self.reg.eq(data)
                write_done(Response.OK)
            else:
                write_done(Response.ERR)

        memorymap = MemoryMapFactory.MemoryMap()
        memorymap.add_resource(self.name, size=1)
        assert memorymap.data_width <= self.reg.width

        m.submodules += platform.BusSlave(
            handle_read, handle_write,
            memorymap=memorymap
        )

        return m
