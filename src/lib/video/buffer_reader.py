from math import ceil

from nmigen import Elaboratable, Module, Signal

from lib.bus.axi.reader import AxiReader
from lib.bus.ring_buffer import RingBufferAddressStorage
from lib.bus.stream.debug import StreamInfo
from lib.peripherals.csr_bank import ControlSignal, StatusSignal
from lib.video.image_stream import ImageStream


class VideoBufferReader(Elaboratable):
    def __init__(self, ring_buffer, bits_per_pixel, width_pixels, height_pixels, stride_pixels=None, data_width=64, address_width=32):
        self.ring_buffer = ring_buffer

        self.bits_per_pixel = bits_per_pixel
        self.width_pixels = width_pixels
        self.height_pixels = height_pixels
        self.stride_pixels = stride_pixels or width_pixels
        self.address_width = address_width
        self.data_width = data_width

        self.output = ImageStream(data_width)

    def elaborate(self, platform):
        m = Module()

        address_generator = m.submodules.address_generator = VideoBufferReaderAddressGenerator(
            self.ring_buffer,
            self.bits_per_pixel, self.width_pixels, self.height_pixels, self.stride_pixels,
            address_width=self.address_width, data_width=self.data_width,
        )
        reader = m.submodules.axi_reader = AxiReader(address_generator.output)
        m.d.comb += self.output.connect_upstream(reader.output)
        m.submodules.output_stream_info = StreamInfo(reader.output)

        return m


class VideoBufferReaderAddressGenerator(Elaboratable):
    def __init__(
            self,
            ringbuffer: RingBufferAddressStorage,
            bits_per_pixel, width_pixels, height_pixels, stride_pixels,
            address_width=32, data_width=64,
    ):
        self.address_width = address_width
        self.data_width_bytes = data_width // 8

        self.stride_bytes = ControlSignal(16, reset=ceil(stride_pixels * bits_per_pixel / 8 / self.data_width_bytes) * self.data_width_bytes)
        self.to_read_x_bytes = ControlSignal(16, reset=ceil(width_pixels * bits_per_pixel / 8 / self.data_width_bytes) * self.data_width_bytes)
        self.to_read_y_lines = ControlSignal(16, reset=height_pixels)

        self.next_frame = Signal()
        self.current_buffer = StatusSignal(ringbuffer.current_write_buffer.shape())
        self.frame_count = StatusSignal(32)

        self.ringbuffer = ringbuffer

        self.output = ImageStream(address_width)

    def elaborate(self, platform):
        m = Module()

        x_ctr = Signal(16)
        y_ctr = Signal(16)
        line_base = Signal(self.address_width, reset=self.ringbuffer.buffer_base_list[0])
        with m.If(self.output.ready & (y_ctr < self.to_read_y_lines)):
            with m.If(x_ctr < self.to_read_x_bytes):
                m.d.comb += self.output.valid.eq(1)
                m.d.sync += self.output.payload.eq(self.output.payload + self.data_width_bytes)
                m.d.sync += x_ctr.eq(x_ctr + self.data_width_bytes)
                with m.If((x_ctr == self.to_read_x_bytes - self.data_width_bytes) & (y_ctr == self.to_read_y_lines - 1)):
                    m.d.comb += self.output.frame_last.eq(1)
                with m.If((x_ctr == self.to_read_x_bytes - self.data_width_bytes)):
                    m.d.comb += self.output.line_last.eq(1)
            with m.Else():
                m.d.sync += x_ctr.eq(0)
                m.d.sync += y_ctr.eq(y_ctr + 1)
                m.d.sync += self.output.payload.eq(
                    line_base + self.stride_bytes
                )
                m.d.sync += line_base.eq(line_base + self.stride_bytes)

        with m.If((y_ctr == self.to_read_y_lines)):
            m.d.sync += self.frame_count.eq(self.frame_count + 1)
            current_buffer = Signal.like(self.current_buffer)
            with m.If(self.ringbuffer.current_write_buffer == 0):
                m.d.comb += current_buffer.eq(len(self.ringbuffer.buffer_base_list) - 1)
            with m.Else():
                m.d.comb += current_buffer.eq(self.ringbuffer.current_write_buffer - 1)
            m.d.sync += x_ctr.eq(0)
            m.d.sync += y_ctr.eq(0)
            m.d.sync += self.current_buffer.eq(current_buffer)
            m.d.sync += self.output.payload.eq(self.ringbuffer.buffer_base_list[self.current_buffer])
            m.d.sync += line_base.eq(self.ringbuffer.buffer_base_list[self.current_buffer])

        m.submodules.output_stream_info = StreamInfo(self.output)

        return m