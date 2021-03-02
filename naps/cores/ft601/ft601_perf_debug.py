# a helper for diagnosing ft601 performance

from nmigen import *

__all__ = ["FT601PerfDebug"]


class FT601PerfDebug(Elaboratable):
    def __init__(self, ft601_resource):
        self.ft_601_resource = ft601_resource
        self.burst_counter = Signal(16)
        self.idle_counter = Signal(16)

    def elaborate(self, platform):
        m = Module()

        ft = self.ft_601_resource

        m.domains += ClockDomain("ft")
        m.d.comb += ClockSignal("ft").eq(ft.clk)

        pause_cycles = 0
        in_transaction = Signal()
        pause_counter = Signal(range(pause_cycles + 1))

        with m.If((ft.txe & in_transaction) | (ft.txe & (pause_counter == pause_cycles))):  # we have space in the transmit fifo
            m.d.ft += self.burst_counter.eq(self.burst_counter + 1)
            m.d.comb += ft.write.eq(1)
            m.d.ft += self.idle_counter.eq(0)
            m.d.ft += in_transaction.eq(1)
            m.d.ft += pause_counter.eq(0)
        with m.Else():
            m.d.ft += self.burst_counter.eq(0)
            m.d.ft += self.idle_counter.eq(self.idle_counter + 1)
            m.d.ft += in_transaction.eq(0)
            with m.If(pause_counter < pause_cycles):
                m.d.ft += pause_counter.eq(pause_counter + 1)

        m.d.comb += ft.be.o.eq(0b1111)  # everything we write is valid
        m.d.comb += ft.oe.eq(0)  # we are driving the data bits all the time
        m.d.comb += ft.data.o.eq(Cat(self.burst_counter, self.idle_counter))

        return m
