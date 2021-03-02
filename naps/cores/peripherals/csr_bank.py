# TODO: implement atomic access (and before think about it)

from nmigen import *
from nmigen import Signal
from naps.soc import MemoryMap, Response, Peripheral
from naps.soc.csr_types import StatusSignal, ControlSignal, EventReg, _Csr

__all__ = ["CsrBank"]


class CsrBank(Elaboratable):
    def __init__(self):
        self.memorymap = MemoryMap()

    def reg(self, name: str, signal: _Csr):
        assert isinstance(signal, _Csr)
        writable = not isinstance(signal, StatusSignal)
        self.memorymap.allocate(name, writable, bits=len(signal), address=signal._address, obj=signal)

    def elaborate(self, platform):
        handled = Signal()

        def handle_read(m, addr, data, read_done):
            for iter_addr in range(0, self.memorymap.byte_len + 1, self.memorymap.bus_word_width_bytes):
                with m.If(iter_addr == addr):
                    for row in self.memorymap.direct_children:
                        bits_of_word = row.address.bits_of_word(iter_addr)
                        if bits_of_word:
                            word_range, signal_range = bits_of_word
                            if isinstance(row.obj, (ControlSignal, StatusSignal)):
                                m.d.sync += data[word_range.start:word_range.stop].eq(
                                    row.obj[signal_range.start:signal_range.stop]
                                )
                                read_done(Response.OK)
                                m.d.comb += handled.eq(1)
                            elif isinstance(row.obj, EventReg):
                                row.obj.handle_read(m, data[word_range.start:word_range.stop], read_done)
                                m.d.comb += handled.eq(1)
                            else:
                                raise NotImplementedError()
            with m.If(~handled):
                read_done(Response.ERR)

        def handle_write(m, addr, data, write_done):
            handled = Signal()
            for iter_addr in range(0, self.memorymap.byte_len + 1, self.memorymap.bus_word_width_bytes):
                with m.If(iter_addr == addr):
                    for row in self.memorymap.direct_children:
                        bits_of_word = row.address.bits_of_word(iter_addr)
                        if bits_of_word and row.writable:
                            word_range, signal_range = bits_of_word
                            if isinstance(row.obj, ControlSignal):
                                m.d.sync += row.obj[signal_range.start:signal_range.stop].eq(
                                    data[word_range.start:word_range.stop]
                                )
                                write_done(Response.OK)
                                m.d.comb += handled.eq(1)
                            elif isinstance(row.obj, StatusSignal):
                                write_done(Response.OK)
                                m.d.comb += handled.eq(1)
                            elif isinstance(row.obj, EventReg):
                                row.obj.handle_write(m, data[word_range.start:word_range.stop], write_done)
                                m.d.comb += handled.eq(1)
                            else:
                                raise NotImplementedError()
            with m.If(~handled):
                write_done(Response.ERR)

        m = Module()
        m.submodules += Peripheral(handle_read, handle_write, self.memorymap)
        return m
