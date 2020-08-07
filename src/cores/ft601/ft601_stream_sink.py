# a helper for interfacing the ft601 usb3 fifo bridge in 245 Synchronous FIFO mode

from nmigen import *

from cores.stream.fifo import AsyncStreamFifo
from util.stream import StreamEndpoint


class FT601StreamSinkNoCDC(Elaboratable):
    def __init__(self, ft601_resource, input_stream: StreamEndpoint):
        self.ft_601_resource = ft601_resource
        assert len(input_stream.payload) == 32
        self.input_stream = input_stream

    def elaborate(self, platform):
        m = Module()

        sink = StreamEndpoint.like(self.input_stream, is_sink=True)
        m.d.comb += sink.connect(self.input_stream)

        ft = self.ft_601_resource

        m.d.comb += ft.be.oe.eq(1)
        m.d.comb += ft.be.o.eq(0b1111)  # everything we write is valid

        m.d.comb += ft.oe.eq(0)  # we are driving the data bits all the time
        m.d.comb += ft.data.oe.eq(1)

        m.d.comb += ft.data.o.eq(sink.payload)
        m.d.comb += sink.ready.eq(ft.txe)
        m.d.comb += ft.write.eq(sink.valid)

        return m


class FT601StreamSink(Elaboratable):
    def __init__(self, ft601_resource, input_stream, fifo_depth=2048):
        self.ft601_resource = ft601_resource
        self.input_stream = input_stream
        self.fifo_depth = fifo_depth

    def elaborate(self, platform):
        m = Module()

        m.domains += ClockDomain("ft601")
        m.d.comb += ClockSignal("ft601").eq(self.ft601_resource.clk)

        cdc_fifo = m.submodules.cdc_fifo = AsyncStreamFifo(self.input_stream, self.fifo_depth, r_domain="ft601", w_domain="sync")
        ft601 = m.submodules.ft601 = DomainRenamer("ft601")(FT601StreamSinkNoCDC(self.ft601_resource, cdc_fifo.output))

        return m
