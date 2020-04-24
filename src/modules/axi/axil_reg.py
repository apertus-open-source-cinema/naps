from modules.axi.axil_slave import AxiLiteSlave
from .axi import Response
from nmigen import *


class AxiLiteReg(Elaboratable):
    def __init__(self, *, width, base_address, writable=True, name=None):
        self.reg = Signal(width, name="{}_csr_reg".format(name))
        self.writable = writable
        self.name = name

        self.axi_slave = AxiLiteSlave(
            address_range=range(base_address, base_address + 1),
            handle_read=self.handle_read,
            handle_write=self.handle_write,
            bundle_name="{}_csr_axi".format(name)
        )
        self.axi = self.axi_slave.axi

        assert width <= len(self.axi.read_data.value)

    def elaborate(self, platform):
        m = Module()
        setattr(m.submodules, "{}_csr_axil_slave".format(self.name), self.axi_slave)
        return m

    def handle_read(self, m, addr, data, resp, read_done):
        m.d.sync += data.eq(self.reg)
        m.d.sync += resp.eq(Response.OKAY)
        read_done()

    def handle_write(self, m, addr, data, resp, write_done):
        if self.writable:
            m.d.sync += self.reg.eq(data)
        m.d.sync += resp.eq(Response.OKAY)
        write_done()
