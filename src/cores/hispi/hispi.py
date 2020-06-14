from nmigen import *

from cores.csr_bank import StatusSignal
from cores.hispi.hispi_phy import HispiPhy
from cores.hispi.hispi_rx import HispiRx


class Hispi(Elaboratable):
    def __init__(self, sensor):
        self.lvds_clk = sensor.lvds_clk
        self.lvds = sensor.lvds

        self.frame_counter = StatusSignal(name='frame_counter')
        self.data_valid = StatusSignal(name='data_valid')

    def elaborate(self, platform):
        m = Module()

        phy = m.submodules.phy = HispiPhy()
        m.d.comb += phy.hispi_clk.eq(self.lvds_clk)
        m.d.comb += phy.hispi_lanes.eq(self.lvds)

        rx = m.submodules.rx = HispiRx(data_in=phy.dout)
        m.d.sync += self.data_valid.eq(rx.decoder.data_valid)
        with m.If(rx.decoder.frame_start):
            m.d.sync += self.frame_counter.eq(self.frame_counter + 1)

        return m