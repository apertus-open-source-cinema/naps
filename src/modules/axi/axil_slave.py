from abc import abstractmethod, ABC

from nmigen import *
from nmigen.back import verilog

from modules.axi.axi import Response, Interface


class AxiLiteSlave(Elaboratable, ABC):
    def __init__(self, *, handle_read, handle_write, address_range):
        """
        A simple (low performance) axi lite slave
        :param handle_read: the callback to insert logic for the read state
        :param handle_write: the callback to insert logic for the write state
        :param address_range: the address space of the axi slave
        """
        assert address_range.start < address_range.stop
        self.address_range = address_range
        assert callable(handle_read) and callable(handle_write)
        self.handle_read = handle_read
        self.handle_write = handle_write

        self.bus = Interface(addr_bits=32, data_bits=32, lite=True)

    def elaborate(self, platform):
        m = Module()

        addr = Signal.like(self.bus.read_address.value)
        read_out = Signal.like(self.bus.read_data.value)
        resp_out = Signal.like(self.bus.read_data.resp)

        with m.FSM():
            with m.State("IDLE"):
                m.d.comb += self.bus.read_address.ready.eq(1)
                m.d.comb += self.bus.write_address.ready.eq(1)

                def in_range(signal, range):
                    return (signal >= range.start) & (signal < range.stop)

                with m.If(self.bus.read_address.valid & in_range(self.bus.read_address.value, self.address_range)):
                    m.d.sync += addr.eq(self.bus.read_address.value - self.address_range.start)
                    m.next = "READ"
                with m.Elif(self.bus.write_address.valid & in_range(self.bus.write_address.value, self.address_range)):
                    m.d.sync += addr.eq(self.bus.write_address.value - self.address_range.start)
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
                m.d.comb += self.bus.read_data.value.eq(read_out)
                m.d.comb += self.bus.read_data.resp.eq(resp_out)
                m.d.comb += self.bus.read_data.valid.eq(1)
                with m.If(self.bus.read_data.ready):
                    m.next = "IDLE"

            with m.State("WRITE"):
                write_done = Signal()
                m.d.comb += self.bus.write_data.ready.eq(write_done)
                with m.If(self.bus.write_data.valid):
                    def set_write_done(): m.d.sync += write_done.eq(1)
                    self.handle_write(m, addr, self.bus.write_data.value, self.bus.write_response.resp, set_write_done)
                    with m.If(write_done):
                        m.d.sync += write_done.eq(0)
                        m.next = "WRITE_DONE"
            with m.State("WRITE_DONE"):
                m.d.comb += self.bus.write_response.valid.eq(1)
                m.d.comb += self.bus.write_data.ready.eq(1)
                with m.If(self.bus.write_response.ready):
                    m.next = "IDLE"

        return m


class AxiLiteSlaveToFullBridge(Elaboratable):
    def __init__(self):
        self.lite_bus = Interface(addr_bits=32, data_bits=32, lite=True)
        self.full_bus = Interface(addr_bits=32, data_bits=32, lite=False, id_bits=12)

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.full_bus.connect(self.lite_bus, exclude = { "read_address": { "id": True }, "write_address": { "id": True }, "read_data": { "id": True }, "write_data": { "id": True }, "write_response": { "id": True } })

        read_id = Signal.like(self.full_bus.read_data.id)
        write_id = Signal.like(self.full_bus.write_data.id)

        with m.If(self.full_bus.read_address.valid):
            m.d.comb += self.full_bus.read_data.id.eq(self.full_bus.read_address.id)
            m.d.sync += read_id.eq(self.full_bus.read_address.id)
        with m.Else():
            m.d.comb += self.full_bus.read_data.id.eq(read_id)

        with m.If(self.full_bus.write_address.valid):
            m.d.comb += self.full_bus.write_data.id.eq(self.full_bus.write_address.id)
            m.d.sync += write_id.eq(self.full_bus.write_address.id)
        with m.Else():
            m.d.comb += self.full_bus.write_data.id.eq(write_id)

        m.d.comb += self.full_bus.read_data.last.eq(1)

        return m
