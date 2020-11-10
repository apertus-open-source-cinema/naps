# An experiment that allows debugging / diagnosing performance of the FT601 USB3 FIFO ic

from nmigen import *

from devices import HdmiDigitizerPlatform, Usb3PluginPlatform
from lib.io.ft601.ft601_perf_debug import FT601PerfDebug
from soc.cli import cli
from soc.platforms import ZynqSocPlatform
from soc.platforms.jtag.jtag_soc_platform import JTAGSocPlatform


class Top(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, platform):
        m = Module()

        ft601 = platform.request("ft601")
        ft601_perf_debug = m.submodules.ft601_perf_debug = FT601PerfDebug(ft601)
        m.d.comb += platform.request("led", 0).eq(1)
        #connect_leds(m, platform, Const(1), upper_bits=False)

        return m


if __name__ == "__main__":
    with cli(Top, runs_on=(Usb3PluginPlatform, HdmiDigitizerPlatform), possible_socs=(JTAGSocPlatform, ZynqSocPlatform)) as platform:
        pass
