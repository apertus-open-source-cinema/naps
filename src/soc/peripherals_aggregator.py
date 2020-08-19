from soc.memorymap import MemoryMap
from util.nmigen_misc import iterator_with_if_elif


class PeripheralsAggregator:
    def __init__(self):
        """
        A helper class that behaves like a Peripheral but proxies its read/write request to downstream peripherals
        based on their memorymap.
        """
        self.downstream_peripherals = []

    def add_peripheral(self, peripheral):
        assert callable(peripheral.handle_read) and callable(peripheral.handle_write)
        assert isinstance(peripheral.memorymap, MemoryMap)
        self.downstream_peripherals.append(peripheral)

    @property
    def range(self):
        return range(
            start=min(*(p.range.start for p in self.downstream_peripherals)),
            stop=max(*(p.range.stop for p in self.downstream_peripherals))
        )

    def handle_read(self, m, addr, data, read_done_callback):
        for cond, peripheral in iterator_with_if_elif(self.downstream_peripherals, m):
            address_range = peripheral.memorymap.own_offset_normal_resources.range()
            with cond((addr >= address_range.start) & (addr < address_range.stop)):
                peripheral.handle_read(m, addr - address_range.start, data, read_done_callback)

    def handle_write(self, m, addr, data, write_done_callback):
        for cond, peripheral in iterator_with_if_elif(self.downstream_peripherals, m):
            address_range = peripheral.memorymap.own_offset_normal_resources.range()
            with cond((addr >= address_range.start) & (addr < address_range.stop)):
                peripheral.handle_write(m, addr - address_range.start, data, write_done_callback)
