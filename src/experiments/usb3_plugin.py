# Experimental gateware for the usb3 plugin module

import unittest

from nmigen import *

from cores.csr_bank import ControlSignal
from cores.ft601.ft601_stream_sink import FT601StreamSink
from cores.plugin_module_streamer.rx import PluginModuleStreamerRx
from cores.stream.counter_source import CounterStreamSource
from devices import Usb3PluginPlatform
from soc.cli import cli
from util.sim import SimPlatform
from util.stream import StreamEndpoint


class Top(Elaboratable):
    def __init__(self):
        self.test_register = ControlSignal()

    def elaborate(self, platform):
        m = Module()

        plugin = platform.request("plugin_stream_input")
        rx = m.submodules.rx = PluginModuleStreamerRx(plugin)

        jtag_analyze = StreamEndpoint(Signal(32), is_sink=False, has_last=False)
        m.d.comb += jtag_analyze.valid.eq(1)
        # m.d.comb += jtag_analyze.payload.eq(platform.jtag_signals)

        in_domain = DomainRenamer("wclk_in")

        counter = m.submodules.counter = in_domain(CounterStreamSource(32))

        ft601 = platform.request("ft601")
        m.submodules.ft601 = in_domain(FT601StreamSink(ft601, counter.output))

        return m


class TestSimulateUsb3Plugin(unittest.TestCase):
    def test_simulate(self):
        dut = Top()

        def testbench():
            for i in range(10000):
                yield

        platform = SimPlatform()
        platform.add_sim_clock("wclk_in", 50e6)
        platform.add_sim_clock("ft601", 100e6)
        platform.sim(dut, testbench)


if __name__ == "__main__":
    with cli(Top, runs_on=(Usb3PluginPlatform,)) as platform:
        pass
