from modules.axi.axil_slave import AxiLiteSlave
from .axi import Response
from nmigen import *


class AxiLiteReg(Elaboratable):
    def __init__(self, *, width, base_address, writable=True, name=None):
        self.reg = Signal(width, name=name)
        self.writable = writable

        self.axi = AxiLiteSlave(
            address_range=range(base_address, base_address + 1),
            handle_read=self.handle_read,
            handle_write=self.handle_write
        )
        self.bus = self.axi.bus

        assert width <= len(self.bus.read_data.value)

    def elaborate(self, platform):
        # TODO: is this evil?
        return self.axi

    def handle_read(self, m, addr, data, resp, read_done):
        m.d.sync += data.eq(self.reg)
        m.d.sync += resp.eq(Response.OKAY)
        read_done()

    def handle_write(self, m, addr, data, resp, write_done):
        if self.writable:
            m.d.sync += self.reg.eq(data)
        m.d.sync += resp.eq(Response.OKAY)
        write_done()
