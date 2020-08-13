# Experimental gateware for the usb3 plugin module

from nmigen import *

from cores.ft601.ft601_stream_sink import FT601StreamSink
from cores.plugin_module_streamer.rx import PluginModuleStreamerRx
from devices import Usb3PluginPlatform
from soc.cli import cli


class Top(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, platform):
        m = Module()

        plugin = platform.request("plugin_stream_input")
        rx = m.submodules.rx = PluginModuleStreamerRx(plugin)

        ft601 = platform.request("ft601")
        m.submodules.ft601 = FT601StreamSink(ft601, rx.output)

        return m


if __name__ == "__main__":
    with cli(Top, runs_on=(Usb3PluginPlatform, )) as platform:
        pass
