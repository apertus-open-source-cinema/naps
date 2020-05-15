# TODO: implement atomic access (and before think about it)
# TODO: implemt event regs (depends on #1)
# TODO: add some kind of arebeiter (is this the right place?; how should it work?)

from nmigen import *

from soc import Response
from soc.SocPlatform import SocPlatform
from soc.memorymap import MemoryMap, Address
from soc.reg_types import EventReg


class CsrBank(Elaboratable):
    def __init__(self, name):
        self.memorymap = MemoryMap(name)

    def reg(self, signal: Signal, writable, address=None):
        self.memorymap.allocate(signal.name, writable, bits=signal.width, address=Address.parse(address), obj=signal)

    def elaborate(self, platform: SocPlatform):
        m = Module()

        def handle_read(m, addr, data, read_done):
            for iter_addr in range(0, self.memorymap.size() + 1, step=self.memorymap.access_width):
                with m.If(iter_addr == addr):
                    for name, (reg_addr, writable, reg) in self.memorymap.entries.items():
                        bits_of_word = reg_addr.bits_of_word(iter_addr)
                        if bits_of_word:
                            word_range, signal_range = bits_of_word
                            if isinstance(reg, Signal):
                                m.d.sync += data[word_range.start:word_range.stop].eq(
                                    reg[signal_range.start:signal_range.stop]
                                )
                                read_done(Response.OK)
                            elif isinstance(reg, EventReg):
                                raise NotImplementedError()
                with m.Else():
                    # unaligned reads are not supported
                    read_done(Response.ERR)

        def handle_write(m, addr, data, write_done):
            for iter_addr in range(0, self.memorymap.size() + 1, step=self.memorymap.access_width):
                with m.If(iter_addr == addr):
                    for name, (reg_addr, writable, reg) in self.memorymap.entries.items():
                        bits_of_word = reg_addr.bits_of_word(iter_addr)
                        if bits_of_word and writable:
                            word_range, signal_range = bits_of_word
                            if isinstance(reg, Signal):
                                m.d.sync += reg[signal_range.start:signal_range.stop].eq(
                                    data[word_range.start:word_range.stop]
                                )
                                write_done(Response.OK)
                            elif isinstance(reg, EventReg):
                                raise NotImplementedError()
                with m.Else():
                    # unaligned reads are not supported
                    write_done(Response.ERR)

        m.submodules += platform.BusSlave(
            handle_read,
            handle_write,
            memorymap=self.memorymap
        )

        return m
