# TODO: figure out api
# TODO: implement

from nmigen import *

from cores.csr_bank import ControlSignal, StatusSignal
from . import AxiEndpoint
from .axi_endpoint import Response
from ..stream.stream import StreamEndpoint


class AxiBufferReader(Elaboratable):
    def __init__(
            self,
            address_source: StreamEndpoint,
            axi_slave=None, axi_data_width=64
    ):
        assert address_source.has_last is False
        self.address_source = address_source
        self.axi_slave = axi_slave
        self.output = StreamEndpoint(Signal(axi_data_width), is_sink=False, has_last=False)

        self.last_resp = StatusSignal(Response)
        self.error_count = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        if self.axi_slave is not None:
            assert not self.axi_slave.is_lite
            assert not self.axi_slave.is_master
            axi_slave = self.axi_slave
        else:
            clock_signal = Signal()
            m.d.comb += clock_signal.eq(ClockSignal())
            axi_slave = platform.get_ps7().get_axi_hp_slave(clock_signal)
        axi = AxiEndpoint.like(axi_slave, master=True)
        m.d.comb += axi.connect_slave(axi_slave)

        assert len(self.output.payload) == axi.data_bits

        address_stream = StreamEndpoint.like(self.address_source, is_sink=True)
        m.d.comb += address_stream.connect(self.address_source)
        assert len(address_stream.payload) == axi.addr_bits

        # we dont generate bursts for now
        m.d.comb += axi.read_address.valid.eq(address_stream.valid)
        m.d.comb += axi.read_address.value.eq(address_stream.payload)
        m.d.comb += address_stream.ready.eq(axi.read_address.ready)
        m.d.comb += axi.read_address.burst_len.eq(0)

        m.d.comb += axi.read_data.ready.eq(self.output.ready)
        m.d.comb += axi.read_data.last.eq(1)
        m.d.comb += self.output.valid.eq(axi.read_data.valid)
        m.d.comb += self.output.payload.eq(axi.read_data.value)

        m.d.sync += self.last_resp.eq(axi.read_data.resp)
        with m.If(axi.read_data.valid & (axi.read_data.resp != Response.OKAY)):
            m.d.sync += self.error_count.eq(self.error_count + 1)

        return m
