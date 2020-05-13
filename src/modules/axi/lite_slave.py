from abc import abstractmethod, ABC

from nmigen import *
from nmigen.back import verilog

from modules.axi.axi import Response, AxiInterface


class AxiLiteSlave(Elaboratable, ABC):
    def __init__(self, handle_read, handle_write, address_range=None, bundle_name="axi"):
        """
        A simple (low performance) axi lite slave
        :param handle_read: the callback to insert logic for the read state
        :param handle_write: the callback to insert logic for the write state
        :param address_range: the address space of the axi slave
        """
        self.address_range = address_range
        assert callable(handle_read) and callable(handle_write)
        self.handle_read = handle_read
        self.handle_write = handle_write

        self.axi = AxiInterface(master=False, addr_bits=32, data_bits=32, lite=True, name=bundle_name)

    def elaborate(self, platform):
        m = Module()

        assert self.address_range is not None
        assert self.address_range.start < self.address_range.stop

        addr = Signal.like(self.axi.read_address.value)
        read_out = Signal.like(self.axi.read_data.value)
        resp_out = Signal.like(self.axi.read_data.resp)

        with m.FSM():
            with m.State("IDLE"):
                m.d.comb += self.axi.read_address.ready.eq(1)
                m.d.comb += self.axi.write_address.ready.eq(1)

                def in_range(signal):
                    return (signal >= self.address_range.start) & (signal < self.address_range.stop)

                with m.If(self.axi.read_address.valid & in_range(self.axi.read_address.value)):
                    m.d.sync += addr.eq(self.axi.read_address.value - self.address_range.start)
                    m.next = "READ"
                with m.Elif(self.axi.write_address.valid & in_range(self.axi.write_address.value)):
                    m.d.sync += addr.eq(self.axi.write_address.value - self.address_range.start)
                    m.next = "WRITE"

            with m.State("READ"):
                # Only write read and resp if we are in the READ state. Otherwise all bits are '0'.
                # This allows us to simply or the data output of multiple axi slaves together.
                read_done = Signal()

                def set_read_done(): m.d.sync += read_done.eq(1)

                self.handle_read(m, addr, read_out, resp_out, set_read_done)
                with m.If(read_done):
                    m.d.sync += read_done.eq(0)
                    m.next = "READ_DONE"
            with m.State("READ_DONE"):
                m.d.comb += self.axi.read_data.value.eq(read_out)
                m.d.comb += self.axi.read_data.resp.eq(resp_out)
                m.d.comb += self.axi.read_data.valid.eq(1)
                with m.If(self.axi.read_data.ready):
                    m.next = "IDLE"

            with m.State("WRITE"):
                write_done = Signal()
                m.d.comb += self.axi.write_data.ready.eq(write_done)
                with m.If(self.axi.write_data.valid):
                    def set_write_done(): m.d.sync += write_done.eq(1)

                    self.handle_write(m, addr, self.axi.write_data.value, self.axi.write_response.resp, set_write_done)
                    with m.If(write_done):
                        m.d.sync += write_done.eq(0)
                        m.next = "WRITE_DONE"
            with m.State("WRITE_DONE"):
                m.d.comb += self.axi.write_response.valid.eq(1)
                m.d.comb += self.axi.write_data.ready.eq(1)
                with m.If(self.axi.write_response.ready):
                    m.next = "IDLE"

        return m
