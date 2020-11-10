from nmigen import *

from lib.bus.axi.reader import AxiReader
from lib.bus.stream.debug import InflexibleSinkDebug, StreamInfo
from lib.bus.stream.fifo import BufferedAsyncStreamFIFO
from lib.bus.stream.gearbox import StreamGearbox
from lib.bus.stream.image_stream import ImageStream
from lib.peripherals.csr_bank import ControlSignal, StatusSignal
from lib.io.hdmi.hdmi import Hdmi
from lib.io.hdmi.parse_modeline import VideoTiming
from lib.bus.ring_buffer import RingBufferAddressStorage
from soc.devicetree.overlay import devicetree_overlay
from util.nmigen_misc import iterator_with_if_elif
from lib.bus.stream.stream import Stream


class HdmiBufferReader(Elaboratable):
    def __init__(self, ring_buffer, hdmi_plugin, modeline, data_interpreter_class: type):
        self.modeline = modeline
        self.hdmi_plugin = hdmi_plugin
        self.ring_buffer = ring_buffer
        self.data_interpreter_class = data_interpreter_class

    def elaborate(self, platform):
        m = Module()

        hdmi = m.submodules.hdmi = Hdmi(self.hdmi_plugin, self.modeline)

        address_generator = m.submodules.address_generator = DomainRenamer("axi_hp")(AddressGenerator(
            self.ring_buffer, hdmi.initial_video_timing,
            pixels_per_word=self.data_interpreter_class.pixels_per_word
        ))
        reader = m.submodules.axi_reader = DomainRenamer("axi_hp")(AxiReader(address_generator.output))
        pixel_fifo = m.submodules.pixel_fifo = BufferedAsyncStreamFIFO(
            reader.output, depth=1024 * 16, w_domain="axi_hp", r_domain="pix"
        )
        gearbox = m.submodules.gearbox = DomainRenamer("pix")(StreamGearbox(
            pixel_fifo.output,
            target_width=len(pixel_fifo.output.payload) // self.data_interpreter_class.pixels_per_word
        ))
        pixel_slipper = m.submodules.pixel_slipper = DomainRenamer("pix")(
            PixelSlipper(gearbox.output, hdmi)
        )
        m.submodules.data_interpreter = DomainRenamer("pix")(
            self.data_interpreter_class(pixel_slipper.output, hdmi, self.ring_buffer)
        )

        m.submodules.pixel_fifo_output_stream_info = DomainRenamer("pix")(
            StreamInfo(pixel_fifo.output)
        )

        return m


class AddressGenerator(Elaboratable):
    def __init__(
            self,
            ringbuffer: RingBufferAddressStorage, initial_video_timing: VideoTiming,
            pixels_per_word=2, total_x=None, address_width=32, data_width=64,
            max_line_width=5000,
    ):
        self.next_frame = Signal()
        self.total_x = ControlSignal(32, reset=total_x or initial_video_timing.hres)
        self.to_read_x = ControlSignal(32, reset=initial_video_timing.hres)
        self.to_read_y = ControlSignal(32, reset=initial_video_timing.vres)

        self.current_buffer = StatusSignal(ringbuffer.current_write_buffer.shape())
        self.frame_count = StatusSignal(32)

        self.pixels_per_word = pixels_per_word
        self.ringbuffer = ringbuffer
        self.address_width = address_width
        self.data_width_bytes = data_width // 8
        self.max_line_width = max_line_width

        self.output = ImageStream(address_width)

    def elaborate(self, platform):
        m = Module()

        x_ctr = Signal(range(self.max_line_width))
        y_ctr = Signal.like(self.to_read_y)
        line_base = Signal(self.address_width, reset=self.ringbuffer.buffer_base_list[0])
        with m.If(self.output.ready & (y_ctr < self.to_read_y)):
            with m.If(x_ctr < self.to_read_x):
                m.d.comb += self.output.valid.eq(1)
                m.d.sync += self.output.payload.eq(self.output.payload + self.data_width_bytes)
                m.d.sync += x_ctr.eq(x_ctr + self.pixels_per_word)
                with m.If((x_ctr == self.to_read_x - self.pixels_per_word) & (y_ctr == self.to_read_y - 1)):
                    m.d.comb += self.output.frame_last.eq(1)
                with m.If((x_ctr == self.to_read_x - self.pixels_per_word)):
                    m.d.comb += self.output.line_last.eq(1)
            with m.Else():
                m.d.sync += x_ctr.eq(0)
                m.d.sync += y_ctr.eq(y_ctr + 1)
                m.d.sync += self.output.payload.eq(
                    line_base + self.total_x * self.data_width_bytes // self.pixels_per_word
                )
                m.d.sync += line_base.eq(line_base + self.total_x * self.data_width_bytes // self.pixels_per_word)

        with m.If((y_ctr == self.to_read_y)):
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


class PixelSlipper(Elaboratable):
    def __init__(self, input: ImageStream, hdmi: Hdmi):
        self.hdmi = hdmi
        self.input = input

        self.allow_slip_h = ControlSignal(reset=1)
        self.allow_slip_v = ControlSignal(reset=1)
        self.slipped_v = StatusSignal(32)
        self.slipped_h = StatusSignal(32)
        self.output = input.clone(name="slipped")

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.input.connect_downstream(self.output)

        was_line_last = Signal()
        was_frame_last = Signal()
        with m.If(self.input.ready):
            m.d.sync += was_line_last.eq(self.input.line_last)
            m.d.sync += was_frame_last.eq(self.input.frame_last)

        with m.If(self.hdmi.timing_generator.is_blanking_x & ~was_line_last & self.allow_slip_h):
            m.d.sync += self.slipped_h.eq(self.slipped_h + 1)
            m.d.comb += self.input.ready.eq(1)
            
        with m.If(self.hdmi.timing_generator.is_blanking_y & ~was_frame_last & self.allow_slip_v):
            m.d.sync += self.slipped_v.eq(self.slipped_v + 1)
            m.d.comb += self.input.ready.eq(1)

        m.submodules.input_stream_info = StreamInfo(self.input)

        return m


class LinuxFramebuffer(Elaboratable):
    """Interprets the data read from memory as rgba 8 bit colors (compatible with the simpleframebuffer linux driver)"""

    pixels_per_word = 2

    def __init__(self, hdmi: Hdmi, ring_buffer: RingBufferAddressStorage):
        self.hdmi = hdmi
        self.ring_buffer = ring_buffer

        self.input: ImageStream

    def elaborate(self, platform):
        m = Module()

        with m.If(self.hdmi.timing_generator.active):
            m.d.comb += self.data.ready.eq(1)

        m.d.comb += self.hdmi.rgb.r.eq(self.data.payload[0:8])
        m.d.comb += self.hdmi.rgb.g.eq(self.data.payload[8:16])
        m.d.comb += self.hdmi.rgb.b.eq(self.data.payload[16:24])

        debug = m.submodules.debug = InflexibleSinkDebug(self.data)

        overlay_content = """
            %overlay_name%: framebuffer@%address% {
                compatible = "simple-framebuffer";
                reg = <0x%address% (%width% * %height% * 4)>;
                width = <%width%>;
                height = <%height%>;
                stride = <(%width% * 4)>;
                format = "a8b8g8r8";
            };
        """
        devicetree_overlay(platform, "framebuffer", overlay_content, {
            "width": str(self.hdmi.initial_video_timing.hres),
            "height": str(self.hdmi.initial_video_timing.vres),
            "address": "{:x}".format(self.ring_buffer.buffer_base_list[len(self.ring_buffer.buffer_base_list) - 1]),
            # we choose the last buffer because there is no writer so the reader always reads from the last buffer
        })

        return m


class FullResDebayerer(Elaboratable):
    """Interprets the data read from memory as 4 * 12bit bayer data"""

    pixels_per_word = 4

    def __init__(self, data: Stream, hdmi: Hdmi, ringbuffer):
        self.hdmi = hdmi
        self.data = data

    def elaborate(self, platform):
        m = Module()

        current_pixel_per_word = Signal(range(self.pixels_per_word))
        for i in iterator_with_if_elif(range(self.pixels_per_word), m):
            pass
        with m.If(self.hdmi.timing_generator.active):
            m.d.sync += current_pixel_per_word.eq(current_pixel_per_word + 1)
            with m.If(current_pixel_per_word == 0):
                m.d.comb += self.data.ready.eq(1)
                m.d.comb += self.hdmi.rgb.r.eq(self.data.payload[0 + 32:8 + 32])
                m.d.comb += self.hdmi.rgb.g.eq(self.data.payload[8 + 32:16 + 32])
                m.d.comb += self.hdmi.rgb.b.eq(self.data.payload[16 + 32:24 + 32])
            with m.Elif(current_pixel_per_word == 1):
                m.d.comb += self.hdmi.rgb.r.eq(self.data.payload[0:8])
                m.d.comb += self.hdmi.rgb.g.eq(self.data.payload[8:16])
                m.d.comb += self.hdmi.rgb.b.eq(self.data.payload[16:24])
        with m.Else():
            m.d.sync += current_pixel_per_word.eq(0)

        return m
