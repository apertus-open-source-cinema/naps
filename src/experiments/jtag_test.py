from nmigen import *

from cores.ft601.ft601_perf_debug import FT601PerfDebug
from cores.ft601.ft601_stream_sink import FT601StreamSink
from cores.stream.counter_source import StreamCounterSource
from soc.cli import cli
from util.instance_helper import InstanceHelper
from xilinx.clocking import Pll


class Top(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, platform):
        m = Module()

        jtag = m.submodules.jtag = InstanceHelper("+/xilinx/cells_xtra.v", "BSCANE2")(jtag_chain=1)
        m.domains += ClockDomain("tck")
        m.d.comb += ClockSignal("tck").eq(jtag.tck)
        dr = Signal(8)
        with m.If(jtag.shift & jtag.sel):
            m.d.tck += dr.eq(Cat(dr[1:], jtag.tdi))

        m.d.comb += jtag.tdo.eq(dr[0])

        for i in range(8):
            m.d.comb += platform.request("led", i).eq(dr[i])

        return m


if __name__ == "__main__":
    with cli(Top) as platform:
        pass
