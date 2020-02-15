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

        addr = Signal.like(self.bus.read_address.value)

        with m.FSM():
            with m.State("IDLE"):
                m.d.comb += self.bus.read_address.ready.eq(1)
                m.d.comb += self.bus.write_address.ready.eq(1)

                with m.If(self.bus.read_address.valid):
                    m.d.sync += addr.eq(self.bus.read_address.value)
                    m.next = "READ"
                with m.Elif(self.bus.write_address.valid):
                    m.d.sync += addr.eq(self.bus.write_address.value)
                    m.next = "WRITE"
            with m.State("READ"):
                self.handle_read(m, addr, self.bus.read_data.value, self.bus.read_data.resp)
                with m.If(self.read_done):
                    m.d.sync += self.read_done.eq(0)
                    m.next = "READ_DONE"
            with m.State("READ_DONE"):
                m.d.comb += self.bus.read_data.valid.eq(1)

                with m.If(self.bus.read_data.ready):
                    m.next = "IDLE"
            with m.State("WRITE"):
                with m.If(self.bus.write_data.valid):
                    self.handle_write(m, addr, self.bus.write_data.value, self.bus.write_response.resp)
                    with m.If(self.write_done):
                        m.d.sync += self.write_done.eq(0)
                        m.next = "WRITE_DONE"
            with m.State("WRITE_DONE"):
                m.d.comb += self.bus.write_response.valid.eq(1)
                m.d.comb += self.bus.write_data.ready.eq(1)
                with m.If(self.bus.write_response.ready):
                    m.next = "IDLE"

        return m


class AxiLiteReg(AxiLiteSlave):
    def __init__(self, *, width, base_address):
        super().__init__()
        assert width <= len(self.bus.read_data.value)
        self.reg = Signal(width)
        self.base_address = base_address

    def handle_read(self, m, addr, data, resp):
        with m.If(addr == self.base_address):
            m.d.sync += data.eq(self.reg)
            m.d.sync += resp.eq(Response.OKAY)
            m.d.sync += self.read_done.eq(1)

    def handle_write(self, m, addr, data, resp):
        with m.If(addr == self.base_address):
            m.d.sync += self.reg.eq(data)
            m.d.sync += resp.eq(Response.OKAY)
            m.d.sync += self.write_done.eq(1)


if __name__ == "__main__":
    pins = Signal(8)
    print(verilog.convert(AxiLiteReg(width=8, base_address=0x00000000)))
