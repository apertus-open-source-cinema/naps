from nmigen import *

from modules.axi.axi import Response, AxiInterface
from modules.axi.lite_slave import AxiLiteSlave
from util.nmigen_types import TristateIo


class AxilI2cVersatileBitbang(Elaboratable):
    I2C_CONTROL = 0x00
    I2C_CONTROL_SET = 0x00
    I2C_CONTROL_CLEAR = 0x04
    SCL = (1 << 0)
    SDA = (1 << 1)

    def __init__(self, axil_master: AxiInterface, base_address, pads):
        """ A simple Axi lite peripheral, that is compatible with the bitbanging i2c versatile linux kernel driver.
        see https://github.com/torvalds/linux/blob/master/drivers/i2c/busses/i2c-versatile.c
        Quite hacky but overall a quite quick solution to get working i2c.
        """
        self._axil_master = axil_master
        self._pads = pads
        self._base_address = base_address

    def elaborate(self, platform):
        m = Module()

        scl: TristateIo = self._pads.scl
        sda: TristateIo = self._pads.sda
        m.d.comb += scl.o.eq(0)
        m.d.comb += sda.o.eq(0)

        def handle_read(m, addr, data, resp, read_done):
            with m.If(addr == self.I2C_CONTROL):
                m.d.sync += data.eq(Cat(scl.i, sda.i))

            m.d.comb += resp.eq(Response.OKAY)
            read_done()

        def handle_write(m, addr, data, resp, write_done):
            with m.If(addr == self.I2C_CONTROL_SET):
                with m.If(data == self.SCL):
                    m.d.sync += scl.oe.eq(1)
                with m.Elif(data == self.SDA):
                    m.d.sync += sda.oe.eq(1)
            with m.Elif(addr == self.I2C_CONTROL_CLEAR):
                with m.If(data == self.SCL):
                    m.d.sync += scl.oe.eq(0)
                with m.Elif(data == self.SDA):
                    m.d.sync += sda.oe.eq(0)

            write_done()
            m.d.sync += resp.eq(Response.OKAY)

        axi_slave = m.submodules.axi_slave = AxiLiteSlave(
            handle_read=handle_read,
            handle_write=handle_write,
            address_range=range(self._base_address, self._base_address + 4)
        )
        m.d.comb += self._axil_master.connect_slave(axi_slave.axi)

        return m
