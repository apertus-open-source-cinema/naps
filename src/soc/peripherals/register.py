from nmigen import *

from soc import Response
from soc.SocPlatform import SocPlatform


class SocRegister(Elaboratable):
    def __init__(self, *, width, writable=True, name=None, reset=0):
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

        memorymap = platform.MemoryMap()
        memorymap.add_resource(self, size=1)
        assert memorymap.data_width <= self.reg.width

        platform.BusSlave(
            handle_read, handle_write,
            memorymap=memorymap
        )

        return m
