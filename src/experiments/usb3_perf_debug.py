from nmigen import *

from cores.ft601.ft601_perf_debug import FT601PerfDebug
from cores.ft601.ft601_stream_sink import FT601StreamSink
from cores.stream.counter_source import StreamCounterSource
from soc.cli import cli
from xilinx.clocking import Pll


class Top(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, platform):
        m = Module()
        ft601 = platform.request("ft601")

        ft601_perf_debug = m.submodules.ft601_perf_debug = FT601PerfDebug(ft601)
        for i in range(8):
            m.d.comb += platform.request("led", i).eq(ft601_perf_debug.idle_counter[(i)])

        return m


if __name__ == "__main__":
    with cli(Top, soc=False) as platform:
        pass
