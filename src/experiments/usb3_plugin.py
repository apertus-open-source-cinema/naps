# Experimental gateware for the usb3 plugin module

from nmigen import *

from devices import Usb3PluginPlatform
from lib.bus.stream.counter_source import CounterStreamSource
from lib.bus.stream.stream import BasicStream
from lib.debug.blink_debug import BlinkDebug
from lib.io.ft601.ft601_stream_sink import FT601StreamSink
from lib.io.plugin_module_streamer.rx import PluginModuleStreamerRx
from lib.peripherals.csr_bank import ControlSignal
from soc.cli import cli
from soc.platforms.jtag.jtag_soc_platform import JTAGSocPlatform


class Top(Elaboratable):
    def __init__(self):
        self.test_register = ControlSignal(32)
        self.test_register2 = ControlSignal(32)

    def elaborate(self, platform):
        m = Module()

        plugin = platform.request("plugin_stream_input")
        rx = m.submodules.rx = PluginModuleStreamerRx(plugin, domain_name="plugin")

        jtag_analyze = BasicStream(32)
        m.d.comb += jtag_analyze.valid.eq(jtag_analyze.ready)
        platform.jtag_signals = jtag_analyze.payload

        ft601 = platform.request("ft601")
        m.submodules.ft601 = FT601StreamSink(ft601, jtag_analyze, domain_name="sync")

        return m


if __name__ == "__main__":
    with cli(Top, runs_on=(Usb3PluginPlatform,), possible_socs=(JTAGSocPlatform,)) as platform:
        pass
