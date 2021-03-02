# Experimental gateware for the usb3 plugin module
from nmigen import *
from naps import *


class Top(Elaboratable):
    def elaborate(self, platform):
        m = Module()

        clocking = m.submodules.clocking = ClockingDebug("sync", "sync_in", "ft601")

        plugin = platform.request("plugin_stream_input")
        rx = m.submodules.rx = PluginModuleStreamerRx(plugin, domain_name="sync")

        ft601 = platform.request("ft601")
        m.submodules.ft601 = FT601StreamSink(ft601, rx.output, domain_name="ft601")

        return m


if __name__ == "__main__":
    cli(Top, runs_on=(Usb3PluginPlatform,), possible_socs=(JTAGSocPlatform,))
