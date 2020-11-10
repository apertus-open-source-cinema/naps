# Experimental gateware for the usb3 plugin module

from nmigen import *

from devices import Usb3PluginPlatform
from lib.bus.stream.counter_source import CounterStreamSource
from lib.bus.stream.stream import BasicStream
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
        rx = m.submodules.rx = PluginModuleStreamerRx(plugin)

        counter = Signal(24)
        m.d.sync += counter.eq(counter + 1)

        jtag_analyze = BasicStream(32)
        m.d.comb += jtag_analyze.payload.eq(platform.jtag_signals)
        m.d.comb += jtag_analyze.valid.eq(1)

        in_domain = DomainRenamer("wclk_in")

        counter = m.submodules.counter = in_domain(CounterStreamSource(32))

        ft601 = platform.request("ft601")
        m.submodules.ft601 = in_domain(FT601StreamSink(ft601, counter.output))

        return m


if __name__ == "__main__":
    with cli(Top, runs_on=(Usb3PluginPlatform,), possible_socs=(JTAGSocPlatform,)) as platform:
        pass
