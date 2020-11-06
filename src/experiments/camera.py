# An experiment that glues everything together and tries to get a full sensor -> hdmi flow working on the micro

import os

from nmigen import *

from cores.axi.buffer_writer import AxiBufferWriter
from cores.debug.clocking_debug import ClockingDebug
from cores.hdmi.cvt_python import generate_modeline
from cores.hispi.hispi import Hispi
from cores.i2c.bitbang_i2c import BitbangI2c
from cores.csr_bank import ControlSignal
from cores.ring_buffer_address_storage import RingBufferAddressStorage
from cores.hdmi.hdmi_buffer_reader import HdmiBufferReader
from cores.stream.fifo import AsyncStreamFifo
from devices import MicroR2Platform
from soc.cli import cli
from soc.platforms import ZynqSocPlatform
from soc.pydriver.drivermethod import driver_method


class Top(Elaboratable):
    def __init__(self):
        self.sensor_reset_n = ControlSignal(name='sensor_reset', reset=1)
        self.writer_reset = ControlSignal(reset=1)

    def elaborate(self, platform):
        m = Module()

        # clocking = m.submodules.clocking = ClockingDebug("sensor_clk", "hispi", "axi_hp")

        # i2c_pads = platform.request("i2c")
        # m.submodules.i2c = BitbangI2c(i2c_pads)
        #
        # sensor = platform.request("sensor")
        # platform.ps7.fck_domain(24e6, "sensor_clk")
        # m.d.comb += sensor.clk.eq(ClockSignal("sensor_clk"))
        # m.d.comb += sensor.reset.eq(~self.sensor_reset_n)
        # # TODO: find more idiomatic way to do this
        # os.environ["NMIGEN_add_constraints"] = \
        #     "set_property CLOCK_DEDICATED_ROUTE FALSE [get_nets pin_sensor_0__lvds_clk/hispi_sensor_0__lvds_clk__i]"

        ring_buffer = RingBufferAddressStorage(buffer_size=0x1000000, n=4)

        # hispi = m.submodules.hispi = Hispi(sensor)

        platform.ps7.fck_domain(200e6, "axi_hp")

        # m.domains += ClockDomain("writer")
        # m.d.comb += ClockSignal("writer").eq(ClockSignal("axi_hp"))
        # m.d.comb += ResetSignal("writer").eq(self.writer_reset)
        # writer_fifo = m.submodules.writer_fifo = AsyncStreamFifo(hispi.output, 2048, r_domain="writer", w_domain="hispi")
        # m.submodules.buffer_writer = DomainRenamer("writer")(AxiBufferWriter(ring_buffer, writer_fifo.output))

        hdmi_plugin = platform.request("hdmi", "north")
        m.submodules.hdmi_buffer_reader = HdmiBufferReader(
            ring_buffer, hdmi_plugin,
            modeline=generate_modeline(1280, 720, 30)
        )

        return m

    @driver_method
    def dump_buffer(self):
        self.writer_reset = 1
        self.writer_reset = 0
        enable_bitslip = self.hispi.phy.enable_bitslip
        self.hispi.phy.enable_bitslip = 0
        from time import sleep
        sleep(0.1)
        from os import system
        system("sudo dd if=/dev/mem bs=4096 skip=260046848 count=16777216 iflag=skip_bytes,count_bytes of=buffer.out")
        self.hispi.phy.enable_bitslip = enable_bitslip


    @driver_method
    def kick_camera(self):
        from os import system
        system("cat /axiom-api/scripts/kick/value")


if __name__ == "__main__":
    with cli(Top, runs_on=(MicroR2Platform,), possible_socs=(ZynqSocPlatform,)) as platform:
        from devices.plugins.hdmi_plugin_resource import hdmi_plugin_connect
        hdmi_plugin_connect(platform, "north")
