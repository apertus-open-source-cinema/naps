from .axi import Response
from .axil_slave import AxiLiteSlave, AxiLiteSlaveToFullBridge
from nmigen import *
from nmigen.back import verilog

class AxiLiteReg(AxiLiteSlave):
    def __init__(self, *, width, base_address):
        super().__init__()
        assert width <= len(self.bus.read_data)
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
