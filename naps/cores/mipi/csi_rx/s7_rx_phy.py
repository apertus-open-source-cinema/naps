from nmigen import *
from naps import ControlSignal
from naps.vendor.xilinx_s7 import BufIO, ClockDivider, IDelay, DDRDeserializer

__all__ = ["MipiClockRxPhy", "MipiLaneRxPhy"]


class MipiClockRxPhy(Elaboratable):
    """Drives the sync domain with the word clock and produces a ddr bit clock derived from the clock lane at `pin`"""
    def __init__(self, pin, ddr_domain):
        self.pin = pin
        self.ddr_domain = ddr_domain

    def elaborate(self, platform):
        m = Module()

        m.domains += ClockDomain(self.ddr_domain)

        bufio = m.submodules.bufio = BufIO(self.pin)
        m.d.comb += ClockSignal(self.ddr_domain).eq(bufio.o)

        divider = m.submodules.divider = ClockDivider(self.pin, divider=4)
        m.d.comb += ClockSignal().eq(divider.o)
        platform.add_clock_constraint(divider.o, 350e6 / 4)

        return m


class MipiLaneRxPhy(Elaboratable):
    def __init__(self, pin, ddr_domain):
        self.pin = pin
        self.ddr_domain = ddr_domain

        self.bitslip = ControlSignal()

        self.output = Signal(8)

    def elaborate(self, platform):
        m = Module()

        delay = m.submodules.delay = IDelay(self.pin)
        serdes = m.submodules.serdes = DDRDeserializer(delay.output, self.ddr_domain, bit_width=8, msb_first=False)
        m.d.comb += serdes.bitslip.eq(self.bitslip)
        m.d.comb += self.output.eq(serdes.output)

        return m
