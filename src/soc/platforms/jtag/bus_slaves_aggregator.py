from nmigen import *

from soc.bus_slave import BusSlave
from util.nmigen_misc import iterator_with_if_elif


class BusSlavesAggregator:
    def __init__(self):
        self.bus_slaves = []

    def add_bus_slave(self, bus_slave):
        assert isinstance(bus_slave, BusSlave)
        self.bus_slaves.append(bus_slave)

    def handle_read(self, m, addr, data, read_done_callback):
        for cond, bus_slave in iterator_with_if_elif(self.bus_slaves, m):
            address_range = bus_slave.memorymap.own_offset_normal_resources.range()
            with cond((addr >= address_range.start) & (addr < address_range.stop)):
                bus_slave.handle_read(m, addr - address_range.start, data, read_done_callback)

    def handle_write(self, m, addr, data, write_done_callback):
        for cond, bus_slave in iterator_with_if_elif(self.bus_slaves, m):
            address_range = bus_slave.memorymap.own_offset_normal_resources.range()
            with cond((addr >= address_range.start) & (addr < address_range.stop)):
                bus_slave.handle_write(m, addr - address_range.start, data, write_done_callback)
