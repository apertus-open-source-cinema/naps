# An experiment that glues everything together and tries to get a full sensor -> hdmi flow working on the micro

import os

from nmigen import *

from cores.axi.buffer_writer import AxiBufferWriter
from cores.debug.clocking_debug import ClockingDebug
from cores.hispi.hispi import Hispi
from cores.hispi.s7_phy import HispiPhy
from cores.i2c.bitbang_i2c import BitbangI2c
from cores.csr_bank import ControlSignal
from cores.ring_buffer_address_storage import RingBufferAddressStorage
from cores.hdmi.hdmi_buffer_reader import HdmiBufferReader
from cores.stream.fifo import AsyncStreamFifo
from devices import MicroR2Platform
from soc.cli import cli
from soc.platforms import ZynqSocPlatform
from util.stream import StreamEndpoint


class Top(Elaboratable):
    def __init__(self):
        self.sensor_reset_n = ControlSignal(name='sensor_reset', reset=1)

    def elaborate(self, platform):
        m = Module()

        clocking = m.submodules.clocking = ClockingDebug("sensor_clk", "hispi", "writer")

        i2c_pads = platform.request("i2c")
        m.submodules.i2c = BitbangI2c(i2c_pads)

        sensor = platform.request("sensor")
        platform.ps7.fck_domain(24e6, "sensor_clk")
        m.d.comb += sensor.clk.eq(ClockSignal("sensor_clk"))
        m.d.comb += sensor.reset.eq(~self.sensor_reset_n)
        # TODO: find more idiomatic way to do this
        os.environ["NMIGEN_add_constraints"] = \
            "set_property CLOCK_DEDICATED_ROUTE FALSE [get_nets pin_sensor_0__lvds_clk/hispi_sensor_0__lvds_clk__i]"

        ring_buffer = RingBufferAddressStorage(buffer_size=0x1000000, n=4)

        hispi = m.submodules.hispi = Hispi(sensor)
        # phy = m.submodules.phy = HispiPhy()
        # m.d.comb += phy.hispi_clk.eq(sensor.lvds_clk)
        # m.d.comb += phy.hispi_lanes.eq(sensor.lvds)
        #
        # counter = Signal(16)
        # m.d.hispi += counter.eq(counter + 1)
        # hispi_phy_stream = StreamEndpoint(64, is_sink=False, has_last=True)
        # m.d.comb += hispi_phy_stream.payload.eq(Cat(phy.out, counter))
        # m.d.comb += hispi_phy_stream.valid.eq(1)

        platform.ps7.fck_domain(200e6, "writer")
        writer_fifo = m.submodules.writer_fifo = AsyncStreamFifo(hispi.output, 2048, r_domain="writer", w_domain="hispi")
        buffer_writer = m.submodules.buffer_writer = DomainRenamer("writer")(AxiBufferWriter(ring_buffer, writer_fifo.output))

        hdmi_plugin = platform.request("hdmi", "north")
        m.submodules.hdmi = HdmiBufferReader(
            ring_buffer, hdmi_plugin,
            modeline='Modeline "Mode 1" 148.500 1920 2008 2052 2200 1080 1084 1089 1125 +hsync +vsync'
        )

        return m


if __name__ == "__main__":
    with cli(Top, runs_on=(MicroR2Platform,), possible_socs=(ZynqSocPlatform,)) as platform:
        from devices.plugins.hdmi_plugin_resource import hdmi_plugin_connect
        hdmi_plugin_connect(platform, "north")
