from nmigen import *
from nmigen.lib.cdc import FFSynchronizer

from lib.bus.axi.buffer_reader import AxiBufferReader
from lib.peripherals.csr_bank import ControlSignal, StatusSignal
from lib.io.hdmi.hdmi import Hdmi
from lib.io.hdmi.parse_modeline import VideoTiming
from lib.bus.ring_buffer import RingBufferAddressStorage
from lib.bus.stream.fifo import AsyncStreamFifo
from soc.devicetree.overlay import devicetree_overlay
from soc.pydriver.drivermethod import driver_property
from util.nmigen_misc import iterator_with_if_elif
from lib.bus.stream.stream import Stream


class HdmiBufferReader(Elaboratable):
    def __init__(self, ring_buffer, hdmi_plugin, modeline, data_interpreter_class: type):
        self.modeline = modeline
        self.hdmi_plugin = hdmi_plugin
        self.ring_buffer = ring_buffer
        self.data_interpreter_class = data_interpreter_class

        self.allow_fifo_reset = ControlSignal()

    def elaborate(self, platform):
        m = Module()

        hdmi = m.submodules.hdmi = Hdmi(self.hdmi_plugin, self.modeline)
        last_blanking_y = Signal()
        m.d.pix += last_blanking_y.eq(hdmi.timing_generator.is_blanking_y)
        begin_blanking_in_axi_domain = Signal()
        m.submodules += FFSynchronizer(
            hdmi.timing_generator.is_blanking_y & ~last_blanking_y,
            begin_blanking_in_axi_domain, o_domain="axi_hp"
        )

        address_generator = m.submodules.address_generator = DomainRenamer("axi_hp")(AddressGenerator(
            self.ring_buffer, hdmi.initial_video_timing,
            pixels_per_word=self.data_interpreter_class.pixels_per_word
        ))
        m.d.comb += address_generator.next_frame.eq(begin_blanking_in_axi_domain)
        reader = m.submodules.axi_reader = DomainRenamer("axi_hp")(AxiBufferReader(address_generator.output))
        m.d.comb += reader.flush.eq(begin_blanking_in_axi_domain)

        m.domains += ClockDomain("buffer_reader_fifo")
        m.d.comb += ClockSignal("buffer_reader_fifo").eq(ClockSignal("axi_hp"))
        m.d.comb += ResetSignal("buffer_reader_fifo").eq(begin_blanking_in_axi_domain & self.allow_fifo_reset)
        pixel_fifo = m.submodules.pixel_fifo = AsyncStreamFifo(
            reader.output, depth=1024 * 16, w_domain="buffer_reader_fifo", r_domain="pix"
        )

        m.submodules.data_interpreter = DomainRenamer("pix")(
            self.data_interpreter_class(pixel_fifo.output, hdmi, self.ring_buffer)
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
        self.disable_framesync = ControlSignal()

        self.current_buffer = StatusSignal(ringbuffer.current_write_buffer.shape())
        self.frame_count = StatusSignal(32)

        self.pixels_per_word = pixels_per_word
        self.ringbuffer = ringbuffer
        self.address_width = address_width
        self.data_width_bytes = data_width // 8
        self.max_line_width = max_line_width

        self.output = Stream(address_width, has_last=True)

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
                with m.If((x_ctr == self.to_read_x - 1) & (y_ctr == self.to_read_y - 1)):
                    m.d.comb += self.output.last.eq(1)
            with m.Else():
                m.d.sync += x_ctr.eq(0)
                m.d.sync += y_ctr.eq(y_ctr + 1)
                m.d.sync += self.output.payload.eq(
                    line_base + self.total_x * self.data_width_bytes // self.pixels_per_word
                )
                m.d.sync += line_base.eq(line_base + self.total_x * self.data_width_bytes // self.pixels_per_word)

        def next_buffer():
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

        with m.If((y_ctr == self.to_read_y) & self.disable_framesync):
            next_buffer()

        last_next_frame = Signal()
        m.d.sync += last_next_frame.eq(self.next_frame)
        with m.If(self.next_frame & ~last_next_frame & ~self.disable_framesync):
            next_buffer()

        return m

    @driver_property
    def fps(self):
        from time import sleep
        start_frames = self.frame_count
        sleep(1)
        return self.frame_count - start_frames


class LinuxFramebuffer(Elaboratable):
    """Interprets the data read from memory as rgba 8 bit colors (compatible with the simpleframebuffer linux driver)"""

    pixels_per_word = 2

    def __init__(self, data: Stream, hdmi: Hdmi, ring_buffer: RingBufferAddressStorage):
        self.data = data
        self.hdmi = hdmi
        self.ring_buffer = ring_buffer

        self.slipped = StatusSignal(32)
        self.last_count = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        fetch_new_pixel = Signal()
        with m.If(self.hdmi.timing_generator.active):
            m.d.sync += fetch_new_pixel.eq(~fetch_new_pixel)
            with m.If(fetch_new_pixel):
                m.d.comb += self.data.ready.eq(1)
                m.d.comb += self.hdmi.rgb.r.eq(self.data.payload[0 + 32:8 + 32])
                m.d.comb += self.hdmi.rgb.g.eq(self.data.payload[8 + 32:16 + 32])
                m.d.comb += self.hdmi.rgb.b.eq(self.data.payload[16 + 32:24 + 32])
            with m.Else():
                m.d.comb += self.hdmi.rgb.r.eq(self.data.payload[0:8])
                m.d.comb += self.hdmi.rgb.g.eq(self.data.payload[8:16])
                m.d.comb += self.hdmi.rgb.b.eq(self.data.payload[16:24])
        with m.Else():
            m.d.sync += fetch_new_pixel.eq(0)

        # last should occur on the last active pixel
        # otherwise the frame is not aligned -> we skip some data during y-blank
        last_occurred = Signal()
        with m.If((self.hdmi.timing_generator.x == 0) & (self.hdmi.timing_generator.y == 0)):
            m.d.sync += last_occurred.eq(0)
        with m.If(self.data.last & (
                self.hdmi.timing_generator.is_blanking_y |
                (self.hdmi.timing_generator.x == self.hdmi.timing_generator.width - 1) |
                (self.hdmi.timing_generator.y == self.hdmi.timing_generator.height - 1)
        )):
            m.d.sync += last_occurred.eq(1)
        with m.If(self.hdmi.timing_generator.is_blanking_y & ~last_occurred):
            with m.If(self.data.last):
                m.d.sync += last_occurred.eq(1)
            m.d.sync += self.slipped.eq(self.slipped + 1)
            m.d.comb += self.data.ready.eq(1)

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
            "address": "{:x}".format(self.ring_buffer.buffer_base_list[len(self.ring_buffer.buffer_base_list)-1]),
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
