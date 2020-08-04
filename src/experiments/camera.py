import os

from nmigen import *

from cores.axi.buffer_writer import AxiBufferWriter
from cores.hispi.hispi import Hispi
from cores.i2c.bitbang_i2c import BitbangI2c
from cores.csr_bank import ControlSignal
from cores.ring_buffer_address_storage import RingBufferAddressStorage
from cores.hdmi.hdmi_buffer_reader import HdmiBufferReader
from soc.cli import cli


class Top(Elaboratable):
    def __init__(self):
        self.sensor_reset_n = ControlSignal(name='sensor_reset', reset=1)

    def elaborate(self, platform):
        m = Module()

        i2c_pads = platform.request("i2c")
        m.submodules.i2c = BitbangI2c(i2c_pads)

        sensor = platform.request("sensor")
        platform.ps7.fck_domain(24e6, "sensor_clk")
        m.d.comb += sensor.clk.eq(ClockSignal("sensor_clk"))
        m.d.comb += sensor.reset.eq(~self.sensor_reset_n)
        # TODO: find more ideomatic way to do this
        os.environ["NMIGEN_add_constraints"] = \
            "set_property CLOCK_DEDICATED_ROUTE FALSE [get_nets pin_sensor_0__lvds_clk/hispi_sensor_0__lvds_clk__i]"

        ring_buffer = RingBufferAddressStorage(buffer_size=0x1200000, n=4)

        hispi = m.submodules.hispi = Hispi(sensor)

        m.domains += ClockDomain("writer")
        m.d.comb += ClockSignal("writer").eq(ClockSignal("hispi"))  # we omit the reset on purpose
        buffer_writer = m.submodules.buffer_writer = DomainRenamer("writer")(AxiBufferWriter(ring_buffer, hispi.output))

        hdmi_plugin = platform.request("hdmi", "north")
        m.submodules.hdmi = HdmiBufferReader(
            ring_buffer, hdmi_plugin,
            modeline='Modeline "Mode 1" 148.500 1920 2008 2052 2200 1080 1084 1089 1125 +hsync +vsync'
        )

        return m


if __name__ == "__main__":
    with cli(Top) as platform:
        from devices.plugins.hdmi import hdmi_plugin_connect
        hdmi_plugin_connect(platform, "north")
