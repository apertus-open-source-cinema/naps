from nmigen import *

from cores.ft601.ft601_stream_sink import FT601StreamSink
from cores.stream.counter_source import StreamCounterSource
from soc.cli import cli
from xilinx.clocking import Pll


class Top(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, platform):
        m = Module()
        # we need a non resetless clock domain
        m.domains += ClockDomain("sync")
        m.d.comb += ClockSignal("sync").eq(platform.request(platform.default_clk))

        ft601 = platform.request("ft601")

        pll = m.submodules.pll = Pll(25e6, vco_mul=40, vco_div=1, input_domain="sync")
        pll.output_domain("fast", 7)
        in_fast_domain = m.submodules.in_fast_domain = DomainRenamer("fast")(InFastDomain(ft601))

        return m


class InFastDomain(Elaboratable):
    def __init__(self, ft601):
        self.ft601 = ft601

    def elaborate(self, platform):
        m = Module()

        counter = m.submodules.counter = StreamCounterSource(32)
        ft601_sink = m.submodules.ft601_sink = FT601StreamSink(self.ft601, counter.output)

        for i in range(8):
            m.d.comb += platform.request("led", i).eq(counter.output.payload[-(i + 1)])



        return m


if __name__ == "__main__":
    with cli(Top) as platform:
        pass
