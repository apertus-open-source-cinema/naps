# TODO: add tests

from nmigen import *
from naps.soc import SocPlatform, Response


__all__ = ["DrpInterface", "DrpBridge"]


# TODO: let this be an `Interface`
class DrpInterface:
    def __init__(self, DWE, DEN, DADDR, DI, DO, DRDY, DCLK):
        self.data_write_enable: Signal = DWE
        self.data_enable: Signal = DEN
        self.address: Signal = DADDR
        self.data_in: Signal = DI
        self.data_out: Signal = DO
        self.ready: Signal = DRDY
        self.clk : Signal = DCLK


class DrpBridge(Elaboratable):
    def __init__(self, drp_interface):
        """
        A bridge for the xilinx dynamic reconfiguration port. This is for example used in the Xilinx 7 series MMCM and
        PLL vendor.

        :param drp_interface: the drp bus of the drp slave
        """
        self.drp_interface: DrpInterface = drp_interface

    def elaborate(self, platform: SocPlatform):
        m = Module()

        def handle_read(m, addr, data, read_done):
            m.d.comb += self.drp_interface.clk.eq(ClockSignal())
            m.d.sync += self.drp_interface.address.eq(addr)
            m.d.sync += self.drp_interface.data_enable.eq(1)
            with m.If(self.drp_interface.ready):
                m.d.sync += self.drp_interface.data_enable.eq(0)
                m.d.sync += data.eq(self.drp_interface.data_out)
                read_done(Response.OK)

        def handle_write(m, addr, data, write_done):
            m.d.comb += self.drp_interface.clk.eq(ClockSignal())
            m.d.sync += self.drp_interface.address.eq(addr)
            m.d.sync += self.drp_interface.data_enable.eq(1)
            m.d.sync += self.drp_interface.data_write_enable.eq(1)
            m.d.sync += self.drp_interface.data_in.eq(data)
            with m.If(self.drp_interface.ready):
                m.d.sync += self.drp_interface.data_enable.eq(0)
                m.d.sync += self.drp_interface.data_write_enable.eq(0)
                write_done(Response.OK)

        # TODO: fix drp bridge
        # memorymap = MemoryMap()
        # memorymap.allocate("drp", writable=True, bits=2**len(self.drp_interface.address) * 8)
        #
        # m.submodules += Peripheral(
        #     handle_read,
        #     handle_write,
        #     memorymap
        # )

        return m
