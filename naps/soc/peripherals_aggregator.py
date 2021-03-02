from .peripheral import Response
from naps.util.nmigen_misc import iterator_with_if_elif

__all__ = ["PeripheralsAggregator"]


class PeripheralsAggregator:
    def __init__(self):
        """
        A helper class that behaves like a Peripheral but proxies its read/write request to downstream peripherals
        based on their memorymap.
        """
        self.downstream_peripherals = []

    def add_peripheral(self, peripheral):
        assert callable(peripheral.handle_read) and callable(peripheral.handle_write)
        assert isinstance(peripheral.range(), range)
        self.downstream_peripherals.append(peripheral)

    def range(self):
        return range(
            min(p.range().start for p in self.downstream_peripherals),
            max(p.range().stop for p in self.downstream_peripherals)
        )

    def handle_read(self, m, addr, data, read_done_callback):
        for cond, peripheral in iterator_with_if_elif(self.downstream_peripherals, m):
            address_range = peripheral.memorymap.absolute_range_of_direct_children.range()
            translated_address_range = range(
                address_range.start - self.range().start,
                address_range.stop - self.range().start,
            )
            with cond((addr >= translated_address_range.start) & (addr < translated_address_range.stop)):
                peripheral.handle_read(m, addr - translated_address_range.start, data, read_done_callback)
        if self.downstream_peripherals:
            with m.Else():
                read_done_callback(Response.ERR)
        else:
            read_done_callback(Response.ERR)

    def handle_write(self, m, addr, data, write_done_callback):
        for cond, peripheral in iterator_with_if_elif(self.downstream_peripherals, m):
            address_range = peripheral.memorymap.absolute_range_of_direct_children.range()
            translated_address_range = range(
                address_range.start - self.range().start,
                address_range.stop - self.range().start,
            )
            with cond((addr >= translated_address_range.start) & (addr < translated_address_range.stop)):
                peripheral.handle_write(m, addr - translated_address_range.start, data, write_done_callback)
        if self.downstream_peripherals:
            with m.Else():
                write_done_callback(Response.ERR)
        else:
            write_done_callback(Response.ERR)
