from nmigen import *

from cores.csr_bank import StatusSignal, ControlSignal
from . import AxiEndpoint
from .axi_endpoint import Response
from util.stream import StreamEndpoint


class AxiBufferReader(Elaboratable):
    def __init__(
            self,
            address_source: StreamEndpoint,
            axi_slave=None, axi_data_width=64
    ):
        assert address_source.has_last is False
        self.address_source = address_source
        self.axi_slave = axi_slave
        self.output = StreamEndpoint(axi_data_width, is_sink=False, has_last=False)
        self.flush = Signal()

        self.last_resp = StatusSignal(Response)
        self.error_count = StatusSignal(32)
        self.outstanding = StatusSignal(32)
        self.state = StatusSignal(2)
        self.allow_flush = ControlSignal()
        self.force_flush = ControlSignal()
        self.limit_outstanding = ControlSignal()
        self.max_outstanding = ControlSignal(32, reset=2048)


    def elaborate(self, platform):
        m = Module()

        if self.axi_slave is not None:
            assert not self.axi_slave.is_lite
            assert not self.axi_slave.is_master
            axi_slave = self.axi_slave
        else:
            clock_signal = Signal()
            m.d.comb += clock_signal.eq(ClockSignal())
            axi_slave = platform.ps7.get_axi_hp_slave(clock_signal)
        axi = AxiEndpoint.like(axi_slave, master=True)
        m.d.comb += axi.connect_slave(axi_slave)

        assert len(self.output.payload) == axi.data_bits

        address_stream = StreamEndpoint.like(self.address_source, is_sink=True, name="address_sink")
        m.d.comb += address_stream.connect(self.address_source)
        assert len(address_stream.payload) == axi.addr_bits

        with m.If(self.force_flush):
            m.d.comb += axi.read_data.ready.eq(1)
        with m.Else():
            with m.FSM():
                def common():
                    m.d.comb += axi.read_address.valid.eq(address_stream.valid)
                    m.d.comb += axi.read_address.value.eq(address_stream.payload)
                    m.d.comb += address_stream.ready.eq(axi.read_address.ready)
                    m.d.comb += axi.read_address.burst_len.eq(0)  # we dont generate bursts

                    m.d.comb += axi.read_data.ready.eq(self.output.ready)
                    m.d.comb += self.output.valid.eq(axi.read_data.valid)
                    m.d.comb += self.output.payload.eq(axi.read_data.value)

                    with m.If(self.flush & (self.outstanding > 1) & self.allow_flush):
                        m.next = "flush"

                with m.State("normal"):
                    m.d.comb += self.state.eq(0)
                    common()
                    with m.If((self.outstanding >= self.max_outstanding) & self.limit_outstanding):
                        m.next = "limit_outstanding"

                with m.State("limit_outstanding"):
                    m.d.comb += self.state.eq(1)
                    common()
                    m.d.comb += address_stream.ready.eq(0)
                    with m.If((self.outstanding < self.max_outstanding) | ~axi.read_data.valid):
                        m.next = "normal"

                with m.State("flush"):
                    m.d.comb += self.state.eq(2)
                    m.d.comb += axi.read_data.ready.eq(1)
                    with m.If(self.outstanding == 0 & ~axi.read_data.ready):
                        m.next = "normal"

        m.d.sync += self.last_resp.eq(axi.read_data.resp)
        with m.If(axi.read_data.valid & (axi.read_data.resp != Response.OKAY)):
            m.d.sync += self.error_count.eq(self.error_count + 1)

        address_written = Signal()
        m.d.comb += address_written.eq(axi.read_address.valid & axi.read_address.ready)
        data_read = Signal()
        m.d.comb += data_read.eq(axi.read_data.valid & axi.read_data.ready)
        with m.If(address_written & ~data_read):
            m.d.sync += self.outstanding.eq(self.outstanding + 1)
        with m.Elif(data_read & ~address_written):
            with m.If(self.outstanding != 0):
                m.d.sync += self.outstanding.eq(self.outstanding - 1)

        return m
