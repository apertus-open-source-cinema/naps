from nmigen import Elaboratable, Module, Signal, Array

from naps.cores import AxiReader, AxiWriter, if_none_get_zynq_hp_port, StreamInfo, LastWrapper, StreamTee
from naps import PacketizedStream, BasicStream, stream_transformer, StatusSignal

__all__ = ["DramPacketRingbufferStreamWriter", "DramPacketRingbufferStreamReader"]


class DramPacketRingbufferStreamWriter(Elaboratable):
    def __init__(
            self,
            input: PacketizedStream,
            max_packet_size, n_buffers, base_address=0x0f80_0000,
            axi=None,
    ):
        self.max_packet_size = max_packet_size
        self.base_address = base_address
        self.n_buffers = n_buffers
        self.axi = axi

        self.buffer_base_list = Array([base_address + max_packet_size * i for i in range(n_buffers)])
        self.buffer_level_list = Array([Signal(range(max_packet_size), name=f'buffer{i}_level') for i in range(n_buffers)])
        self.current_write_buffer = Signal(range(n_buffers))

        assert hasattr(input, "last")
        self.input = input

        self.overflowed_buffers = StatusSignal(32)
        self.buffers_written = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        axi = if_none_get_zynq_hp_port(self.axi, m, platform)
        assert len(self.input.payload) <= axi.data_bits

        tee = m.submodules.tee = StreamTee(self.input)

        data_stream = BasicStream(self.input.payload.shape())
        m.d.comb += data_stream.connect_upstream(tee.get_output(), allow_partial=True)

        transformer_input = tee.get_output()
        address_stream = BasicStream(axi.write_address.payload.shape())
        address_offset = Signal.like(axi.write_address.payload)
        is_in_overflow = Signal()
        stream_transformer(transformer_input, address_stream, m, latency=1, handle_out_of_band=False)

        with m.If(transformer_input.ready & transformer_input.valid):
            m.d.sync += self.buffer_level_list[self.current_write_buffer].eq(address_offset + axi.data_bytes)
            with m.If(transformer_input.last):
                m.d.sync += is_in_overflow.eq(0)
                next_buffer = (self.current_write_buffer + 1) % self.n_buffers
                m.d.sync += address_offset.eq(0)
                m.d.sync += self.current_write_buffer.eq(next_buffer)
                m.d.sync += self.buffers_written.eq(self.buffers_written + 1)
            with m.Else():
                with m.If((address_offset + axi.data_bytes < self.max_packet_size)):
                    m.d.sync += address_offset.eq(address_offset + axi.data_bytes)
                with m.Else():
                    with m.If(~is_in_overflow):
                        m.d.sync += is_in_overflow.eq(1)
                        m.d.sync += self.overflowed_buffers.eq(self.overflowed_buffers + 1)
            m.d.sync += address_stream.payload.eq(address_offset + self.buffer_base_list[self.current_write_buffer])

        m.submodules.writer = AxiWriter(address_stream, data_stream, axi)

        m.submodules.input_stream_info = StreamInfo(self.input)

        return m


class DramPacketRingbufferStreamReader(Elaboratable):
    def __init__(self, writer: DramPacketRingbufferStreamWriter, data_width=64, length_fifo_depth=1, axi=None):
        self.writer = writer
        self.data_width = data_width
        self.length_fifo_depth = length_fifo_depth
        self.axi = axi

        self.current_read_buffer = StatusSignal(self.writer.current_write_buffer.shape())

        self.output = PacketizedStream(data_width)

    def elaborate(self, platform):
        m = Module()

        axi = if_none_get_zynq_hp_port(self.axi, m, platform)
        assert len(self.output.payload) == axi.data_bits
        writer = self.writer

        address_stream = PacketizedStream(axi.read_address.payload.shape())
        m.submodules.address_stream_info = StreamInfo(address_stream)

        address_offset = Signal.like(axi.read_address.payload)

        with m.If(address_offset < writer.buffer_level_list[self.current_read_buffer]):
            m.d.comb += address_stream.valid.eq(1)
            m.d.comb += address_stream.payload.eq(address_offset + writer.buffer_base_list[self.current_read_buffer])
            m.d.comb += address_stream.last.eq(address_offset + axi.data_bytes >= writer.buffer_level_list[self.current_read_buffer])
            with m.If(address_stream.ready):
                m.d.sync += address_offset.eq(address_offset + axi.data_bytes)
        with m.Else():
            next_buffer = Signal.like(self.current_read_buffer)
            with m.If(writer.current_write_buffer == 0):
                m.d.comb += next_buffer.eq(writer.n_buffers - 1)
            with m.Else():
                m.d.comb += next_buffer.eq(writer.current_write_buffer - 1)
            m.d.sync += self.current_read_buffer.eq(next_buffer)
            m.d.sync += address_offset.eq(0)

        reader = m.submodules.axi_reader = LastWrapper(address_stream, lambda i: AxiReader(i, axi=axi, axi_data_width=len(self.output.payload)), last_fifo_depth=10, last_rle_bits=32)
        m.d.comb += self.output.connect_upstream(reader.output)

        m.submodules.output_stream_info = StreamInfo(self.output)

        return m
