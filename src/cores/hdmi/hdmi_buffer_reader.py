from nmigen import *
from nmigen.hdl.ast import Rose
from nmigen.lib.cdc import FFSynchronizer

from cores.axi.buffer_reader import AxiBufferReader
from cores.csr_bank import ControlSignal, StatusSignal
from cores.hdmi.hdmi import Hdmi
from cores.ring_buffer_address_storage import RingBufferAddressStorage
from cores.stream.fifo import AsyncStreamFifo
from util.stream import StreamEndpoint
from util.nmigen_misc import log2


class AddressGenerator(Elaboratable):
    def __init__(
            self,
            ringbuffer: RingBufferAddressStorage,
            max_line_width=5000, address_width=32, data_width=64,
    ):
        self.next_frame = Signal()
        self.line_words_total = ControlSignal(32, reset=2304 // 4)
        self.line_words_read = StatusSignal(32)
        self.read_buffer = StatusSignal(ringbuffer.current_write_buffer.shape())
        self.frames_read = StatusSignal(32)

        self.ringbuffer = ringbuffer
        self.address_width = address_width
        self.data_width = data_width
        self.max_line_width = max_line_width

        self.output = StreamEndpoint(address_width, is_sink=False, has_last=False)

    def elaborate(self, platform):
        m = Module()

        line_ctr = Signal(range(self.max_line_width))
        line_base = Signal(self.address_width)
        with m.If(self.output.ready):
            m.d.sync += self.output.valid.eq(1)
            with m.If(line_ctr < self.line_words_read):
                m.d.sync += self.output.payload.eq(self.output.payload + log2(self.data_width))
                m.d.sync += line_ctr.eq(line_ctr + 1)
            with m.Else():
                m.d.sync += line_ctr.eq(0)
                m.d.sync += self.output.payload.eq(line_base + self.line_words_total)
                m.d.sync += line_base.eq(line_base + self.line_words_total)

        last_next_frame = Signal()
        m.d.sync += last_next_frame.eq(self.next_frame)
        with m.If(self.next_frame & ~last_next_frame):
            m.d.sync += self.frames_read.eq(self.frames_read + 1)
            with m.If(self.ringbuffer.current_write_buffer == 0):
                m.d.comb += self.read_buffer.eq(len(self.ringbuffer.buffer_base_list) - 1)
            with m.Else():
                m.d.comb += self.read_buffer.eq(self.ringbuffer.current_write_buffer - 1)
            m.d.sync += self.output.payload.eq(self.ringbuffer.buffer_base_list[self.read_buffer])
            m.d.sync += line_base.eq(self.ringbuffer.buffer_base_list[self.read_buffer])

        return m


class HdmiBufferReader(Elaboratable):
    def __init__(self, ring_buffer, hdmi_plugin, modeline):
        self.modeline = modeline
        self.hdmi_plugin = hdmi_plugin
        self.ring_buffer = ring_buffer

    def elaborate(self, platform):
        m = Module()

        hdmi = m.submodules.hdmi = Hdmi(self.hdmi_plugin, self.modeline)

        addr_gen = m.submodules.addr_gen = DomainRenamer("axi_hp")(AddressGenerator(self.ring_buffer))
        m.d.comb += addr_gen.line_words_read.eq(hdmi.timing_generator.width)
        m.submodules.next_frame_sync = FFSynchronizer(i=hdmi.timing_generator.blanking_y, o=addr_gen.next_frame, o_domain="axi_hp")
        reader = m.submodules.reader = DomainRenamer("axi_hp")(AxiBufferReader(addr_gen.output))

        m.domains += ClockDomain("buffer_reader_fifo")
        m.d.comb += ClockSignal("buffer_reader_fifo").eq(ClockSignal("axi_hp"))
        last_blanking_y = Signal()
        m.d.pix += last_blanking_y.eq(hdmi.timing_generator.blanking_y)
        m.d.comb += ResetSignal("buffer_reader_fifo").eq(hdmi.timing_generator.blanking_y & ~last_blanking_y)
        pixel_fifo = m.submodules.pixel_fifo = AsyncStreamFifo(reader.output, depth=128, w_domain="buffer_reader_fifo", r_domain="pix")

        output = StreamEndpoint.like(pixel_fifo.output, is_sink=True, name="hdmi_reader_output_sink")
        m.d.comb += output.connect(pixel_fifo.output)

        value = Signal(12)
        ctr = Signal(range(4))
        with m.If(hdmi.timing_generator.active):
            with m.If(ctr == 3):
                m.d.comb += output.ready.eq(1)
                m.d.pix += ctr.eq(0)
            with m.Else():
                m.d.pix += ctr.eq(ctr + 1)
            for i in range(4):
                with m.If(ctr == i):
                    m.d.comb += value.eq(output.payload[i * 12:i * 12 + 12])
        with m.Else():
            m.d.pix += ctr.eq(0)

        m.d.comb += hdmi.rgb.r.eq(value)
        m.d.comb += hdmi.rgb.g.eq(value)
        m.d.comb += hdmi.rgb.b.eq(value)

        return m
