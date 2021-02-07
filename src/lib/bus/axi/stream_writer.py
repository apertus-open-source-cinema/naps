from nmigen import *

from lib.bus.axi.axi_endpoint import AddressStream, DataStream, BurstType, Response
from lib.bus.axi.zynq_util import if_none_get_zynq_hp_port
from lib.bus.stream.debug import StreamInfo
from lib.bus.stream.fifo import BufferedSyncStreamFIFO
from lib.bus.stream.stream import BasicStream
from lib.peripherals.csr_bank import StatusSignal


class AxiWriter(Elaboratable):
    def __init__(
            self,
            address_source: BasicStream,
            data_source: BasicStream,
            axi=None
    ):
        self.address_source = address_source
        self.data_source = data_source
        self.axi = axi

        self.axi_address_ready = StatusSignal()
        self.axi_data_ready = StatusSignal()
        self.write_response_ok = StatusSignal(32)
        self.write_response_err = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        burster = m.submodules.burster = AxiWriterBurster(self.address_source, self.data_source)

        axi = if_none_get_zynq_hp_port(self.axi, m, platform)
        for fifo_signal_name in ["write_address_fifo_level", "write_data_fifo_level"]:
            if hasattr(axi, fifo_signal_name):
                axi_fifo_signal = getattr(axi, fifo_signal_name)
                fifo_signal = StatusSignal(axi_fifo_signal.shape(), name=f"axi_{fifo_signal_name}")
                m.d.comb += fifo_signal.eq(axi_fifo_signal)
                setattr(self, f"axi_{fifo_signal_name}", fifo_signal)

        m.d.comb += axi.write_data.connect_upstream(burster.data_output)
        m.d.comb += axi.write_address.connect_upstream(burster.address_output)

        # we do not currently care about the write responses
        m.d.comb += axi.write_response.ready.eq(1)
        with m.If(axi.write_response.valid):
            with m.If(axi.write_response.resp == Response.OKAY):
                m.d.sync += self.write_response_ok.eq(self.write_response_ok + 1)
            with m.Else():
                m.d.sync += self.write_response_err.eq(self.write_response_err + 1)

        m.d.comb += self.axi_data_ready.eq(axi.write_data.ready)
        m.d.comb += self.axi_address_ready.eq(axi.write_address.ready)

        info_axi_address = m.submodules.info_axi_address = StreamInfo(axi.write_address)
        info_axi_data = m.submodules.info_axi_data = StreamInfo(axi.write_data)

        return m


class AxiWriterBurster(Elaboratable):
    """Creates Write bursts. Outputs Burst addresses on the address Channel and modifies the Data channels last accordingly."""

    def __init__(
            self,
            address_source: BasicStream,
            data_source: BasicStream,
            max_burst_length=16, burst_creation_timeout=31,
            data_fifo_depth=128,
    ):
        self.max_burst_length = max_burst_length
        self.burst_creation_timeout = burst_creation_timeout
        self.word_bytes = len(data_source.payload) // 8
        self.data_fifo_depth = data_fifo_depth

        self.address_input = address_source
        self.data_input = data_source

        self.written_address_bursts_for_n_wards = StatusSignal(32)

        self.address_output = AddressStream(addr_bits=len(address_source.payload), lite=False, id_bits=12, data_bytes=self.word_bytes)
        self.data_output = DataStream(data_bits=len(data_source.payload), read=False, lite=False, id_bits=12)

    def elaborate(self, platform):
        m = Module()

        timeout_counter = Signal(range(self.burst_creation_timeout))

        # burst len is NOT the same representation as in the AXI bus
        # we encode 1 for a burst for 1 data word while AXI would encode that as 0.
        # we use the 0 value to encode, that no data burst is in progress
        # (important for the timeout logic)
        burst_len = Signal(range(self.max_burst_length + 1))
        burst_start_address = Signal.like(self.address_input.payload)
        last_address = Signal.like(self.address_input.payload)
        last_data = Signal.like(self.data_input.payload)

        # we buffer data_output in a FIFO to be able to have outstanding transactions & work with axi masters that expect
        # that the address is transmitted first (like our simulation model)
        data_output = self.data_output.clone(name="data_output_before_fifo")
        data_fifo = m.submodules.data_fifo = BufferedSyncStreamFIFO(data_output, self.data_fifo_depth)
        m.d.comb += self.data_output.connect_upstream(data_fifo.output, allow_partial=True)

        def finish_burst():
            # for calling this function, data_ready must be 1
            with m.If(self.address_output.ready):
                with m.If(self.address_input.valid & self.data_input.valid):
                    m.d.comb += self.data_input.ready.eq(1)
                    m.d.sync += last_data.eq(self.data_input.payload)
                    m.d.sync += burst_len.eq(1)
                    m.d.sync += burst_start_address.eq(self.address_input.payload)
                    m.d.comb += self.address_input.ready.eq(1)
                    m.d.sync += last_address.eq(self.address_input.payload)
                with m.Else():
                    m.d.sync += burst_len.eq(0)
            with m.If(burst_len > 0):
                m.d.comb += self.address_output.valid.eq(1)
                m.d.comb += self.address_output.payload.eq(burst_start_address)
                m.d.comb += self.address_output.burst_len.eq(burst_len - 1)
                m.d.comb += self.address_output.burst_type.eq(BurstType.INCR)
                with m.If(self.address_output.ready):
                    m.d.comb += data_output.valid.eq(1)
                    m.d.comb += data_output.last.eq(1)
                    m.d.comb += data_output.payload.eq(last_data)
                    m.d.comb += data_output.byte_strobe.eq(-1)

        def enlarge_burst():
            # for calling this function, self.address_input.valid, self.data_input.valid, data_output.ready must be 1
            m.d.comb += self.data_input.ready.eq(1)
            m.d.comb += data_output.valid.eq(1)
            m.d.comb += data_output.payload.eq(last_data)
            m.d.sync += last_data.eq(self.data_input.payload)
            m.d.comb += data_output.byte_strobe.eq(-1)

            m.d.comb += self.address_input.ready.eq(1)
            m.d.sync += burst_len.eq(burst_len + 1)
            m.d.sync += last_address.eq(self.address_input.payload)

        with m.If(self.address_input.valid & self.data_input.valid & data_output.ready):
            m.d.sync += timeout_counter.eq(0)
            with m.If((self.address_input.payload == (last_address + self.word_bytes)) & (burst_len < self.max_burst_length - 1)):
                enlarge_burst()
            with m.Else():
                finish_burst()
        with m.Elif((burst_len > 0) & (timeout_counter == self.burst_creation_timeout - 1) & data_output.ready):
            finish_burst()
        with m.Elif((burst_len > 0) & data_output.ready & self.address_output.ready):
            m.d.sync += timeout_counter.eq(timeout_counter + 1)

        m.d.comb += self.address_output.id.eq(self.address_output.id.reset)
        m.d.comb += self.address_output.beat_size_bytes.eq(self.address_output.beat_size_bytes.reset)
        m.d.comb += self.address_output.protection_type.eq(self.address_output.protection_type.reset)
        m.d.comb += data_output.id.eq(data_output.id.reset)

        with m.If(self.address_output.ready & self.address_output.valid):
            m.d.sync += self.written_address_bursts_for_n_wards.eq(self.written_address_bursts_for_n_wards + self.address_output.burst_len + 1)

        return m
