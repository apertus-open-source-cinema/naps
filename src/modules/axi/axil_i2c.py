from nmigen import *

from modules.axi.axil_slave import AxiLiteSlave
from modules.vendor.glasgow_i2c.i2c import I2CInitiator


class AxiLiteI2c(Elaboratable):
    def __init__(self, pads, clock_divider, base_address, address_bytes):
        self.addr_bytes = address_bytes
        self.clock_divider = clock_divider
        self.pads = pads

        self.i2c = I2CInitiator(self.pads, period_cyc=self.clock_divider)
        self.axi = AxiLiteSlave(
            address_range=range(base_address, base_address + 2 ** (8 * address_bytes)),
            handle_read=self.handle_read,
            handle_write=self.handle_write
        )
        self.bus = self.axi.bus

    def elaborate(self, platform):
        m = Module()

        m.submodules.axi =  self.axi
        m.submodules.i2c = self.i2c

        return m

    def handle_read(self, m, addr, data, resp, read_done):
        pass

    def handle_write(self, m, addr, data, resp, write_done):
        i2c = self.i2c
        m.d.sync += i2c.data_i.eq(addr)
