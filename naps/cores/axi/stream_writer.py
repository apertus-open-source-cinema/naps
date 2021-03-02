from nmigen import *
from naps import StatusSignal, BasicStream, PacketizedStream
from naps.cores import StreamInfo, BufferedSyncStreamFIFO, StreamTee
from .axi_endpoint import AxiAddressStream, AxiDataStream, AxiResponse
from .stream_reader import AxiReaderBurster
from .zynq_util import if_none_get_zynq_hp_port

__all__ = ["AxiWriter"]


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
                axi_fifo_signal = axi[fifo_signal_name]
                fifo_signal = StatusSignal(axi_fifo_signal.shape(), name=f"axi_{fifo_signal_name}")
                m.d.comb += fifo_signal.eq(axi_fifo_signal)
                setattr(self, f"axi_{fifo_signal_name}", fifo_signal)

        m.d.comb += axi.write_data.connect_upstream(burster.data_output)
        m.d.comb += axi.write_address.connect_upstream(burster.address_output)

        # we do not currently care about the write responses
        m.d.comb += axi.write_response.ready.eq(1)
        with m.If(axi.write_response.valid):
            with m.If(axi.write_response.resp == AxiResponse.OKAY):
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
            data_fifo_depth=16,
    ):
        self.max_burst_length = max_burst_length
        self.burst_creation_timeout = burst_creation_timeout
        self.word_bytes = len(data_source.payload) // 8
        self.data_fifo_depth = data_fifo_depth

        self.address_input = address_source
        self.data_input = data_source

        self.written_address_bursts_for_n_wards = StatusSignal(32)

        self.address_output = AxiAddressStream(addr_bits=len(address_source.payload), lite=False, id_bits=12, data_bytes=self.word_bytes)
        self.data_output = AxiDataStream(data_bits=len(data_source.payload), read=False, lite=False, id_bits=12)

    def elaborate(self, platform):
        m = Module()
        address_burster = m.submodules.address_burster = AxiReaderBurster(self.address_input, self.word_bytes, self.max_burst_length, self.burst_creation_timeout)
        burst_tee = m.submodules.burst_tee = StreamTee(address_burster.output)
        m.d.comb += self.address_output.connect_upstream(burst_tee.get_output())

        burst_stream = burst_tee.get_output()
        packet_length_stream = BasicStream(burst_stream.burst_len.shape())
        m.d.comb += packet_length_stream.valid.eq(burst_stream.valid)
        m.d.comb += burst_stream.ready.eq(packet_length_stream.ready)
        m.d.comb += packet_length_stream.payload.eq(burst_stream.burst_len)

        data_fifo = m.submodules.data_fifo = BufferedSyncStreamFIFO(self.data_input, self.data_fifo_depth)
        stream_packetizer = m.submodules.stream_packetizer = StreamPacketizer(packet_length_stream, data_fifo.output)
        m.d.comb += self.data_output.connect_upstream(stream_packetizer.output, allow_partial=True)
        m.d.comb += self.data_output.id.eq(self.data_output.id.reset)
        m.d.comb += self.data_output.byte_strobe.eq(-1)

        return m


class StreamPacketizer(Elaboratable):
    def __init__(self, packet_length_stream: BasicStream, data_stream: BasicStream):
        self.packet_length_stream = packet_length_stream
        self.data_stream = data_stream

        self.output = PacketizedStream(self.data_stream.payload.shape())

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.output.payload.eq(self.data_stream.payload)

        packet_counter = Signal(self.packet_length_stream.payload.shape())
        with m.If(self.packet_length_stream.valid & self.data_stream.valid):
            m.d.comb += self.output.valid.eq(1)
            with m.If(self.output.ready):
                m.d.comb += self.data_stream.ready.eq(1)

            with m.If(packet_counter < self.packet_length_stream.payload):
                with m.If(self.output.ready):
                    m.d.sync += packet_counter.eq(packet_counter + 1)
            with m.Else():
                m.d.comb += self.output.last.eq(1)
                with m.If(self.output.ready):
                    m.d.comb += self.packet_length_stream.ready.eq(1)
                    m.d.sync += packet_counter.eq(0)

        return m
