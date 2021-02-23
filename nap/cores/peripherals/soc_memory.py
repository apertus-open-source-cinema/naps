from nmigen import *
from nap.soc import SocPlatform, MemoryMap, Peripheral, Response

__all__ = ["SocMemory"]


class SocMemory(Elaboratable):
    """A memory that can be read / written to by the soc"""

    def __init__(self, *, width, depth, init=None, name=None, soc_read=True, soc_write=True):
        self.memory = Memory(width=width, depth=depth, init=init, name=name)
        self.soc_read = soc_read
        self.soc_write = soc_write
        self.depth = depth

    def elaborate(self, platform):
        m = Module()

        memory = m.submodules.memory = self.memory
        if isinstance(platform, SocPlatform):
            if self.soc_read:
                read_port = m.submodules.soc_read_port = memory.read_port(domain="sync", transparent=False)

                def handle_read(m, addr, data, read_done):
                    with m.If(addr > self.depth - 1):
                        read_done(Response.ERR)
                    with m.Else():
                        with m.FSM():
                            with m.State("ADDR"):
                                m.d.comb += read_port.addr.eq(addr)
                                m.d.comb += read_port.en.eq(1)
                                m.next = "DATA"
                            with m.State("DATA"):
                                m.d.comb += data.eq(read_port.data)
                                read_done(Response.OK)
                                m.next = "ADDR"
            else:
                def handle_read(m, addr, data, read_done):
                    read_done(Response.ERR)

            if self.soc_write:
                write_port = m.submodules.soc_write_port = memory.write_port(domain="sync", transparent=False)

                def handle_write(m, addr, data, write_done):
                    with m.If(addr > self.depth - 1):
                        write_done(Response.ERR)
                    with m.Else():
                        m.d.comb += write_port.addr.eq(addr)
                        m.d.comb += write_port.en.eq(1)
                        m.d.comb += write_port.data.eq(data)
                        write_done(Response.OK)
            else:
                def handle_write(m, addr, data, write_done):
                    write_done(Response.ERR)

            memorymap = MemoryMap()
            memorymap.allocate("drp", writable=True, bits=self.depth * memorymap.bus_word_width)

            m.submodules += Peripheral(
                handle_read,
                handle_write,
                memorymap
            )

        return m

    def read_port(self, *args, **kwargs):
        return self.memory.read_port(*args, **kwargs)

    def write_port(self, *args, **kwargs):
        return self.memory.write_port(*args, **kwargs)