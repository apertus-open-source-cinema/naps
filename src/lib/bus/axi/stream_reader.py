from math import log2

from nmigen import *

from lib.bus.stream.stream import BasicStream
from lib.peripherals.csr_bank import StatusSignal
from .axi_endpoint import Response, AddressStream, BurstType
from .zynq_util import if_none_get_zynq_hp_port
from ..stream.debug import StreamInfo


class AxiReader(Elaboratable):
    def __init__(
            self,
            address_source: BasicStream,
            axi=None, axi_data_width=64,
    ):
        self.address_source = address_source
        self.axi = axi

        self.output = BasicStream(axi_data_width, name="buffer_reader_output_stream")
        self.output.payload = Signal(axi_data_width)

        self.last_resp = StatusSignal(Response)
        self.error_count = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        axi = if_none_get_zynq_hp_port(self.axi, m, platform)
        assert len(self.output.payload) == axi.data_bits
        assert len(self.address_source.payload) == axi.addr_bits

        burster = m.submodules.burster = AxiReaderBurster(self.address_source, data_bytes=axi.data_bytes)
        m.d.comb += axi.read_address.connect_upstream(burster.output)
        m.d.comb += self.output.connect_upstream(axi.read_data, allow_partial=True)

        return m


class AxiReaderBurster(Elaboratable):
    """Creates Read Bursts. Outputs fewer (bursted) read addresses on its output that are equivalent to the input."""
    def __init__(
            self,
            address_source: BasicStream, data_bytes=8,
            max_burst_length=16, burst_creation_timeout=31,
    ):
        self.max_burst_length = max_burst_length
        self.burst_creation_timeout = burst_creation_timeout
        self.data_bytes = data_bytes
        self.input = address_source

        self.output = AddressStream(addr_bits=len(self.input.payload), lite=False, id_bits=12, data_bytes=data_bytes)

    def elaborate(self, platform):
        m = Module()

        burst_ctr = Signal(range(self.max_burst_length + 1))
        timeout_ctr = Signal(range(self.burst_creation_timeout))
        burst_start = Signal.like(self.input.payload)
        last_address = Signal.like(self.input.payload)

        def write_address_burst():
            with m.If(burst_ctr > 0):
                m.d.comb += self.output.valid.eq(1)
                m.d.comb += self.output.payload.eq(burst_start)
                m.d.comb += self.output.burst_type.eq(BurstType.INCR)
                m.d.comb += self.output.burst_len.eq(burst_ctr - 1)

        with m.If((self.input.payload == last_address + self.data_bytes) &
                  (burst_ctr < self.max_burst_length) &
                  self.input.valid):
            m.d.comb += self.input.ready.eq(1)
            m.d.sync += last_address.eq(self.input.payload)
            m.d.sync += burst_ctr.eq(burst_ctr + 1)
            m.d.sync += timeout_ctr.eq(0)
            with m.If(burst_ctr == 0):
                m.d.sync += burst_start.eq(self.input.payload)

        with m.Else():
            with m.If(self.input.valid):
                write_address_burst()
                with m.If(self.output.ready):
                    m.d.comb += self.input.ready.eq(1)
                    m.d.sync += last_address.eq(self.input.payload)
                    m.d.sync += burst_start.eq(self.input.payload)
                    m.d.sync += burst_ctr.eq(1)
                    m.d.sync += timeout_ctr.eq(0)
            with m.Elif((burst_ctr > 0)):
                with m.If(timeout_ctr < self.burst_creation_timeout - 1):
                    m.d.sync += timeout_ctr.eq(timeout_ctr + 1)
                with m.Else():
                    write_address_burst()
                    with m.If(self.output.ready):
                        m.d.comb += self.input.ready.eq(1)
                        m.d.sync += burst_ctr.eq(0)

        m.d.comb += self.output.id.eq(self.output.id.reset)
        m.d.comb += self.output.beat_size_bytes.eq(self.output.beat_size_bytes.reset)
        m.d.comb += self.output.protection_type.eq(self.output.protection_type.reset)

        return m