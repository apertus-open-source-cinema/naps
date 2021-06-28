# set up SPI connection to CMV12k control pins

from nmigen import *
from naps import *

class Co: pass

class Top(Elaboratable):
    def __init__(self):
        self.spi_clks = StatusSignal(32)
        self.actual_cs = StatusSignal(1)
        self.sensor_reset_n = ControlSignal(name='sensor_reset', reset=1)

    def elaborate(self, platform: BetaPlatform):
        m = Module()

        platform.ps7.fck_domain(requested_frequency=100e6)

        sensor = platform.request("sensor")
        platform.ps7.fck_domain(250e6, "sensor_clk")
        m.d.comb += sensor.lvds_clk.eq(ClockSignal("sensor_clk"))
        m.d.comb += sensor.reset.eq(~self.sensor_reset_n)

        spi_pads = platform.request("sensor_spi")
        p = Co()
        p.clk = spi_pads.clk
        p.copi = spi_pads.copi
        p.cipo = spi_pads.cipo
        pcs = Co()
        pcs.o = Signal()
        m.d.comb += spi_pads.cs.eq(~pcs.o)
        p.cs = pcs

        m.d.sync += self.actual_cs.eq(spi_pads.cs)

        m.submodules.spi = BitbangSPI(p)

        last_clk = Signal()
        m.d.sync += last_clk.eq(spi_pads.clk)
        with m.If(~last_clk & spi_pads.clk):
            m.d.sync += self.spi_clks.eq(self.spi_clks + 1)

        clocking_debug = m.submodules.clocking_debug = ClockingDebug("sync")

        return m


if __name__ == "__main__":
    cli(Top, runs_on=(BetaPlatform, ), possible_socs=(ZynqSocPlatform, ))
