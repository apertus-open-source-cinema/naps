from nmigen import *

from cores.axi.buffer_reader import AxiBufferReader
from cores.csr_bank import ControlSignal, StatusSignal
from cores.hdmi.hdmi import Hdmi
from cores.ring_buffer_address_storage import RingBufferAddressStorage
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

        self.ringbuffer = ringbuffer
        self.address_width = address_width
        self.data_width = data_width
        self.max_line_width = max_line_width

        self.output = StreamEndpoint(Signal(address_width), is_sink=False, has_last=False)

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

        with m.If(self.next_frame):
            read_buffer = Signal.like(self.ringbuffer.current_write_buffer)
            with m.If(self.ringbuffer.current_write_buffer == 0):
                m.d.comb += read_buffer.eq(len(self.ringbuffer.buffer_base_list) - 1)
            with m.Else():
                m.d.comb += read_buffer.eq(self.ringbuffer.current_write_buffer - 1)
            m.d.sync += self.output.payload.eq(self.ringbuffer.buffer_base_list[read_buffer])
            m.d.sync += line_base.eq(self.ringbuffer.buffer_base_list[read_buffer])

        return m


class HdmiBufferReader(Elaboratable):
    def __init__(self, ring_buffer, hdmi_plugin, modeline):
        self.modeline = modeline
        self.hdmi_plugin = hdmi_plugin
        self.ring_buffer = ring_buffer

    def elaborate(self, platform):
        m = Module()

        hdmi = m.submodules.hdmi = Hdmi(self.hdmi_plugin, self.modeline)

        in_pix_domain = DomainRenamer("pix")

        addr_gen = m.submodules.addr_gen = in_pix_domain(AddressGenerator(self.ring_buffer))
        m.d.comb += addr_gen.next_frame.eq(hdmi.timing_generator.vsync)
        m.d.comb += addr_gen.line_words_read.eq(hdmi.timing_generator.width)

        reader = m.submodules.reader = in_pix_domain(AxiBufferReader(addr_gen.output))
        output = StreamEndpoint.like(reader.output, is_sink=True)
        m.d.comb += output.connect(reader.output)

        ctr = Signal(range(4))
        with m.If(ctr == 3):
            m.d.comb += output.ready.eq(1)
            m.d.pix += ctr.eq(0)
        with m.Else():
            m.d.pix += ctr.eq(ctr + 1)
        value = Signal(8)
        for i in range(4):
            with m.If(ctr == i):
                m.d.comb += value.eq(output.payload[i * 12:i * 12 + 8])

        m.d.comb += hdmi.rgb.r.eq(value)
        m.d.comb += hdmi.rgb.g.eq(value)
        m.d.comb += hdmi.rgb.b.eq(value)

        return m
