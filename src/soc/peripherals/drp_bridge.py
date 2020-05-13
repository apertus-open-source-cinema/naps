from nmigen import *

from modules.axi.axi import Response, AxiInterface
from modules.axi.lite_slave import AxiLiteSlave
from util.bundle import Bundle


class DrpInterface(Bundle):
    def __init__(self, DWE, DEN, DADDR, DI, DO, DRDY):
        super().__init__()
        self.data_write_enable: Signal = DWE
        self.data_enable: Signal = DEN
        self.address: Signal = DADDR
        self.data_in: Signal = DI
        self.data_out: Signal = DO
        self.ready: Signal = DRDY


class AxilDrpBridge(Elaboratable):
    def __init__(self, axil_master, drp_interface, base_address):
        """
        A bridge for the xilinx dynamic reconfiguration port. This is for example used in the Xilinx 7 series MMCM and
        PLL primitives.

        :param axil_master: the axi master to attach the bridge to
        :param drp_interface: the drp interface of the drp slave
        :param base_address: the base address (on the axi bus) of the drp peripheral
        """
        self.base_address = base_address
        self.axil_master: AxiInterface = axil_master
        self.drp_interface: DrpInterface = drp_interface

    def elaborate(self, platform):
        m = Module()

        def handle_read(m, addr, data, resp, read_done):
            m.d.sync += self.drp_interface.address.eq(addr)
            m.d.sync += self.drp_interface.data_enable.eq(1)
            with m.If(self.drp_interface.ready):
                m.d.sync += self.drp_interface.data_enable.eq(0)
                m.d.sync += data.eq(self.drp_interface.data_out)
                m.d.sync += resp.eq(Response.OKAY)
                read_done()

        def handle_write(m, addr, data, resp, write_done):
            m.d.sync += self.drp_interface.address.eq(addr)
            m.d.sync += self.drp_interface.data_enable.eq(1)
            m.d.sync += self.drp_interface.data_write_enable.eq(1)
            m.d.sync += self.drp_interface.data_in.eq(data)
            with m.If(self.drp_interface.ready):
                m.d.sync += self.drp_interface.data_enable.eq(0)
                m.d.sync += self.drp_interface.data_write_enable.eq(0)
                m.d.sync += resp.eq(Response.OKAY)
                write_done()

        m.submodules.axil_slave = AxiLiteSlave(
            handle_read=handle_read,
            handle_write=handle_write,
            address_range=range(self.base_address, self.base_address + (2**self.drp_interface.address.width)),
        )

        return m
