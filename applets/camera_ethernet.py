# An experiment that glues everything together and tries to get a full sensor -> ethernet flow working on the micro
import os
from nmigen import *
from naps import *


class Top(Elaboratable):
    def __init__(self):
        self.sensor_reset_n = ControlSignal(name='sensor_reset', reset=1)

    def elaborate(self, platform):
        m = Module()

        platform.ps7.fck_domain(100e6, "axi_hp")

        # Control Pane
        i2c_pads = platform.request("i2c")
        m.submodules.i2c = BitbangI2c(i2c_pads)

        # Input Pipeline
        sensor = platform.request("sensor")
        platform.ps7.fck_domain(24e6, "sensor_clk")
        m.d.comb += sensor.clk.eq(ClockSignal("sensor_clk"))
        m.d.comb += sensor.reset.eq(~self.sensor_reset_n)
        # TODO: find more idiomatic way to do this
        os.environ["NMIGEN_add_constraints"] = \
            "set_property CLOCK_DEDICATED_ROUTE FALSE [get_nets pin_sensor_0__lvds_clk/input_hispi_rx_sensor_0__lvds_clk__i]"

        p = Pipeline(m)
        p += HispiRx(sensor, hispi_domain="hispi")
        p += Repack12BitStream(p.output)

        p += BufferedAsyncStreamFIFO(p.output, 2048, o_domain="axi_hp")
        p += StreamGearbox(p.output, 64)
        p += ImageStream2PacketizedStream(p.output)
        p += DramPacketRingbufferStreamWriter(p.output, max_packet_size=0x800000, n_buffers=4)
        p += DramPacketRingbufferCpuReader(p.last)

        return m

    @driver_method
    def kick_sensor(self):
        from os import system
        system("cat /axiom-api/scripts/kick/value")


if __name__ == "__main__":
    cli(Top, runs_on=(MicroR2Platform,), possible_socs=(ZynqSocPlatform,))
