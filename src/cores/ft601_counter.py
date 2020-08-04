# a helper for interfacing the ft601 usb3 fifo bridge in 245 Synchronous FIFO mode

from nmigen import *


class FT601Counter(Elaboratable):
    def __init__(self, ft601_resource):
        self.ft_601_resource = ft601_resource
        self.counter = Signal(32)

    def elaborate(self, platform):
        m = Module()

        ft = self.ft_601_resource

        m.domains += ClockDomain("sync")
        m.d.comb += ClockSignal("sync").eq(ft.clk)

        with m.If(ft.txe):  # we have space in the transmit fifo
            m.d.sync += self.counter.eq(self.counter + 1)

        m.d.comb += ft.be.oe.eq(1)
        m.d.comb += ft.be.o.eq(-1)  # everything we write is valid
        m.d.comb += ft.write.eq(1)  # we are always good to be written

        m.d.comb += ft.oe.eq(0)  # we are driving the data bits all the time
        m.d.comb += ft.data.oe.eq(1)
        m.d.comb += ft.data.o.eq(self.counter)

        return m
