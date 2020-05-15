# TODO: finish
# TODO: add tests
# TODO: port to new register infrastructure

from nmigen import *

from modules.axi.lite_slave import AxiLiteSlave
from soc.SocPlatform import SocPlatform
from util.nmigen_types import TristateIo


class MmioGpio(Elaboratable):
    def __init__(self, pads):
        """ A simple gpio peripheral, that is compatible with the gpio-mmio.c linux kernel driver.
        see https://github.com/torvalds/linux/blob/master/drivers/gpio/gpio-mmio.c
        """
        self._pads = pads

        # registers


    def elaborate(self, platform: SocPlatform):
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
