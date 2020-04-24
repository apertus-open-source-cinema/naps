from nmigen import *
from nmigen.lib.fifo import SyncFIFO

from modules.axi.axi import AxiInterface


class AddressGenerator(Elaboratable):
    def __init__(self, buffer_base_list, max_buffer_size, addr_bits):
        self.buffer_base_list = buffer_base_list
        self.max_buffer_size = max_buffer_size

        self.request = Signal()
        self.change_buffer = Signal()
        self.addr = Signal(addr_bits, reset=buffer_base_list[0])

    def elaborate(self, platform):
        m = Module()

        num_buffers = len(self.buffer_base_list)
        base_addrs = Array(self.buffer_base_list)
        current_buffer = Signal(range(num_buffers))

        with m.If(self.change_buffer):
            m.d.sync += self.addr.eq(base_addrs[current_buffer+1])
            m.d.sync += current_buffer.eq(current_buffer+1)
        with m.Elif(self.request & (self.addr - base_addrs[current_buffer] < self.max_buffer_size)):
            m.d.sync += self.addr.eq(self.addr+1)

        return m


class AxiHpWriter(Elaboratable):
    def __init__(self, axi_master: AxiInterface, buffer_base_list, max_buffer_size=0x40000000, fifo_depth=64):
        assert not axi_master.is_lite
        assert axi_master.is_master
        self.axi = AxiInterface.like(axi_master, master=False)
        self.address_generator = AddressGenerator(buffer_base_list, max_buffer_size, self.axi.addr_bits)

        self.fifo_depth=fifo_depth

        self.data_valid = Signal()  # input
        self.data = Signal(self.axi.data_bits)  # input
        self.change_buffer = Signal()  # input
        self.ready = Signal()  # output

    def elaborate(self, platform):
        m = Module()

        addr_fifo = m.submodules.addr_fifo = SyncFIFO(width=self.axi.addr_bits, depth=self.fifo_depth)
        data_fifo = m.submodules.data_fifo = SyncFIFO(width=self.axi.data_bits, depth=self.fifo_depth)

        m.d.comb += self.ready.eq(addr_fifo.w_rdy & data_fifo.w_rdy)
        with m.If(self.ready):
            m.d.comb += self.address_generator.request.eq(self.data_valid)
            m.d.comb += addr_fifo.w_en.eq(self.address_generator.addr)
            m.d.comb += data_fifo.w_data.eq(self.data)


        return m
