# a helper for interfacing the ft601 usb3 fifo bridge in 245 Synchronous FIFO mode

from nmigen import *
from naps import Stream
from naps.cores import BufferedAsyncStreamFIFO

__all__ = ["FT601StreamSink", "FT601StreamSinkNoCDC"]


class FT601StreamSinkNoCDC(Elaboratable):
    def __init__(self, ft601_resource, input: Stream, save_to_begin_new_transaction=None):
        self.ft_601_resource = ft601_resource
        assert len(input.payload) == 32
        self.input = input
        self.safe_to_begin_new_transaction = save_to_begin_new_transaction

    def elaborate(self, platform):
        m = Module()

        ft = self.ft_601_resource

        m.d.comb += ft.be.o.eq(0b1111)  # everything we write is valid

        m.d.comb += ft.oe.eq(0)  # we are driving the data bits all the time

        if self.safe_to_begin_new_transaction is None:
            m.d.comb += ft.data.o.eq(self.input.payload)
            m.d.comb += self.input.ready.eq(ft.txe)
            m.d.comb += ft.write.eq(self.input.valid)
        else:
            in_transaction = Signal()
            m.d.sync += in_transaction.eq(ft.write)
            with m.If(in_transaction):
                m.d.comb += ft.write.eq(self.input.valid & ft.txe)
                m.d.comb += self.input.ready.eq(ft.txe)
            with m.Else():
                m.d.comb += self.input.ready.eq(ft.txe & self.safe_to_begin_new_transaction)
                m.d.comb += ft.write.eq(self.input.valid & self.safe_to_begin_new_transaction)
            m.d.comb += ft.data.o.eq(self.input.payload)

        return m


class FT601StreamSink(Elaboratable):
    def __init__(self, ft601_resource, input_stream, begin_transactions_at_level=2040, domain_name="ft601"):
        self.domain_name = domain_name
        self.ft601_resource = ft601_resource
        self.input_stream = input_stream
        self.begin_transactions_at_level = begin_transactions_at_level

    def elaborate(self, platform):
        m = Module()

        m.domains += ClockDomain(self.domain_name)
        m.d.comb += ClockSignal(self.domain_name).eq(self.ft601_resource.clk)

        cdc_fifo = m.submodules.cdc_fifo = BufferedAsyncStreamFIFO(
            self.input_stream, self.begin_transactions_at_level + 1, i_domain="sync", o_domain=self.domain_name
        )

        save_to_begin_new_transaction = Signal()
        m.d.comb += save_to_begin_new_transaction.eq(cdc_fifo.r_level >= self.begin_transactions_at_level)

        m.submodules.ft601 = DomainRenamer(self.domain_name)(FT601StreamSinkNoCDC(
            self.ft601_resource,
            cdc_fifo.output,
            save_to_begin_new_transaction,
        ))

        return m
