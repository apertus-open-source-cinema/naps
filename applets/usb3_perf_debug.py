# An experiment that allows debugging / diagnosing performance of the FT601 USB3 FIFO ic
from nmigen import *
from naps import *


class Top(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, platform):
        m = Module()

        ft601 = platform.request("ft601")
        ft601_perf_debug = m.submodules.ft601_perf_debug = FT601PerfDebug(ft601)
        m.d.comb += platform.request("led", 0).eq(1)

        return m


if __name__ == "__main__":
    cli(Top, runs_on=(Usb3PluginPlatform, HdmiDigitizerPlatform), possible_socs=(JTAGSocPlatform, ZynqSocPlatform))
