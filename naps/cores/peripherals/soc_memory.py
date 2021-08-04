from math import ceil
from nmigen import *

from naps import iterator_with_if_elif
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
        self.width = width
        self.split_stages = ceil(self.width / 32)
        self.ports = []


    def handle_read(self, m, addr, data, read_done):
        addr = addr[2:]
        m.submodules += self.ports
        if self.soc_read:
            read_port = self.memory.read_port(domain="sync", transparent=False)
            m.submodules += read_port
            with m.If(addr > (self.depth * self.split_stages) - 1):
                read_done(Response.ERR)
            with m.Else():
                is_read = Signal()
                m.d.comb += is_read.eq(1)
                with m.If(Rose(m, is_read)):
                    m.d.comb += read_port.addr.eq(addr // self.split_stages)
                with m.Else():
                    for cond, i in iterator_with_if_elif(range(self.split_stages), m):
                        with cond(((addr % self.split_stages) == i) if self.split_stages != 1 else True):  # yosys seems to be unable to optimize n % 1 == 0 to 1
                            m.d.sync += data.eq(read_port.data[32 * i:])
                    read_done(Response.OK)
        else:
            read_done(Response.ERR)

    def handle_write(self, m, addr, data, write_done):
        addr = addr[2:]
        if self.soc_write:
            write_port = self.memory.write_port(domain="sync", granularity=self.width if self.split_stages == 1 else 32)
            m.submodules += write_port
            with m.If(addr > (self.depth * self.split_stages) - 1):
                write_done(Response.ERR)
            with m.Else():
                m.d.comb += write_port.addr.eq(addr // self.split_stages)
                for cond, i in iterator_with_if_elif(range(self.split_stages), m):
                    with cond(((addr % self.split_stages) == i) if self.split_stages != 1 else True):  # yosys seems to be unable to optimize n % 1 == 0 to 1
                        m.d.comb += write_port.data.eq(data << (i * 32))
                        m.d.comb += write_port.en.eq(1 << i)
                write_done(Response.OK)

        else:
            write_done(Response.ERR)

    def elaborate(self, platform):
        m = Module()

        if not isinstance(platform, SocPlatform):
            return m

        memorymap = MemoryMap()
        assert memorymap.bus_word_width == 32
        memorymap.allocate("memory", writable=True, bits=self.depth * self.split_stages * memorymap.bus_word_width)
        m.submodules += Peripheral(
            self.handle_read,
            self.handle_write,
            memorymap
        )

        return m

    def read_port(self, domain="sync", **kwargs):
        outer_self = self
        comb = domain == "comb"

        class SocMemoryReadPort(Elaboratable):
            def __init__(self):
                self.read_port = outer_self.memory.read_port(domain="comb" if comb else "sync", **kwargs)

            def elaborate(self, platform):
                nonlocal comb
                nonlocal outer_self

                if not hasattr(platform, "soc_memory_domains_counter"):
                    platform.soc_memory_domains_counter = 0
                else:
                    platform.soc_memory_domains_counter += 1
                domain_name = f"soc_memory_domain_{platform.soc_memory_domains_counter}"

                dr = DomainRenamer(domain_name) if not comb else (lambda x: x)
                outer_self.ports.append(dr(self.read_port))

                m = Module()
                m.domains += (cd := ClockDomain(domain_name))
                m.d.comb += cd.clk.eq(ClockSignal())
                return DomainRenamer(domain)(m)

            def __getattr__(self, item):
                return getattr(self.read_port, item)

        return SocMemoryReadPort()

    def write_port(self, domain="sync", **kwargs):
        outer_self = self

        class SocMemoryWritePort(Elaboratable):
            def __init__(self):
                self.write_port = outer_self.memory.write_port(domain="sync", **kwargs)

            def elaborate(self, platform):
                if not hasattr(platform, "soc_memory_domains_counter"):
                    platform.soc_memory_domains_counter = 0
                else:
                    platform.soc_memory_domains_counter += 1
                domain_name = f"soc_memory_domain_{platform.soc_memory_domains_counter}"

                outer_self.ports.append(DomainRenamer(domain_name)(self.write_port))

                m = Module()
                m.domains += (cd := ClockDomain(domain_name))
                m.d.comb += cd.clk.eq(ClockSignal())
                return DomainRenamer(domain)(m)

            def __getattr__(self, item):
                return getattr(self.write_port, item)

        return SocMemoryWritePort()


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
