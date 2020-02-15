from abc import abstractmethod, ABC

from nmigen import *
from nmigen.back import verilog

from modules.axi.axi import Response, Interface


class AxiLiteSlave(Elaboratable, ABC):
    def __init__(self):
        self.bus = Interface(addr_bits=32, data_bits=32, lite=True)
        self.read_done = Signal()
        self.write_done = Signal()

    @abstractmethod
    def handle_read(self, m, addr, data, resp):
        pass

    @abstractmethod
    def handle_write(self, m, addr, data, resp):
        pass

    def elaborate(self, platform):
        m = Module()

        addr = Signal.like(self.bus.read_address.addr)

        with m.FSM():
            with m.State("IDLE"):
                m.d.comb += self.bus.read_address.ready.eq(1)
                m.d.comb += self.bus.write_address.ready.eq(1)

                with m.If(self.bus.read_address.valid):
                    m.d.sync += addr.eq(self.bus.read_address.addr)
                    m.next = "READ"
                with m.Elif(self.bus.write_address.valid):
                    m.d.sync += addr.eq(self.bus.write_address.addr)
                    m.next = "WRITE"
            with m.State("READ"):
                self.handle_read(m, addr, self.bus.read_data.data, self.bus.read_data.resp)
                with m.If(self.read_done):
                    m.d.sync += self.read_done.eq(0)
                    m.next = "READ_DONE"
            with m.State("READ_DONE"):
                m.d.comb += self.bus.read_data.valid.eq(1)

                with m.If(self.bus.read_data.ready):
                    m.next = "IDLE"
            with m.State("WRITE"):
                m.d.comb += self.bus.write_data.ready.eq(self.write_done)
                with m.If(self.bus.write_data.valid):
                    self.handle_write(m, addr, self.bus.write_data.data, self.bus.write_response.resp)
                    with m.If(self.write_done):
                        m.d.sync += self.write_done.eq(0)
                        m.next = "WRITE_DONE"
            with m.State("WRITE_DONE"):
                m.d.comb += self.bus.write_response.valid.eq(1)
                with m.If(self.bus.write_response.ready):
                    m.next = "IDLE"

        return m

# def connect_lossy()

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
