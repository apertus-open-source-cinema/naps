# TODO: implement atomic access (and before think about it)
# TODO: implemt event regs (depends on #1)
# TODO: add some kind of arebeiter (is this the right place?; how should it work?)

from nmigen import *

from soc import Response
from soc.memorymap import MemoryMap, Address
from soc.reg_types import EventReg


class CsrBank(Elaboratable):
    def __init__(self):
        self.memorymap = MemoryMap()

    def reg(self, name: str, signal: Signal, writable, address=None):
        self.memorymap.allocate(name, writable, bits=signal.width, address=Address.parse(address), obj=signal)

    def elaborate(self, platform):
        m = Module()

        def handle_read(m, addr, data, read_done):
            for iter_addr in range(0, self.memorymap.byte_len + 1, self.memorymap.bus_word_width_bytes):
                with m.If(iter_addr == addr):
                    for row in self.memorymap.normal_resources:
                        bits_of_word = row.address.bits_of_word(iter_addr)
                        if bits_of_word:
                            word_range, signal_range = bits_of_word
                            if isinstance(row.obj, Signal):
                                m.d.sync += data[word_range.start:word_range.stop].eq(
                                    row.obj[signal_range.start:signal_range.stop]
                                )
                                read_done(Response.OK)
                            elif isinstance(row.obj, EventReg):
                                raise NotImplementedError()
                with m.Else():
                    # unaligned reads are not supported
                    read_done(Response.ERR)

        def handle_write(m, addr, data, write_done):
            for iter_addr in range(0, self.memorymap.byte_len + 1, self.memorymap.bus_word_width_bytes):
                with m.If(iter_addr == addr):
                    for row in self.memorymap.normal_resources:
                        bits_of_word = row.address.bits_of_word(iter_addr)
                        if bits_of_word and row.writable:
                            word_range, signal_range = bits_of_word
                            if isinstance(row.obj, Signal):
                                m.d.sync += row.obj[signal_range.start:signal_range.stop].eq(
                                    data[word_range.start:word_range.stop]
                                )
                                write_done(Response.OK)
                            elif isinstance(row.obj, EventReg):
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
