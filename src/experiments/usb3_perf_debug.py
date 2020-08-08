# An experiment that allows debugging / diagnosing performance of the FT601 USB3 FIFO ic
from itertools import count

from nmigen import *
from nmigen.build import ResourceError

from cores.ft601.ft601_perf_debug import FT601PerfDebug
from devices import HdmiDigitizerPlatform, Usb3PluginPlatform
from soc.cli import cli
from util.nmigen_misc import connect_leds


class Top(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, platform):
        m = Module()
        ft601 = platform.request("ft601")

        ft601_perf_debug = m.submodules.ft601_perf_debug = FT601PerfDebug(ft601)
        connect_leds(m, platform, ft601_perf_debug.idle_counter, upper_bits=False)

        return m


if __name__ == "__main__":
    with cli(Top, runs_on=(Usb3PluginPlatform, HdmiDigitizerPlatform)) as platform:
        pass
