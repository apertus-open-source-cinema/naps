from nmigen import *

from naps import ControlSignal, StatusSignal
from naps.cores import InflexibleSinkDebug, StreamInfo, ImageStream, RGB24
from .hdmi_tx import HdmiTx

__all__ = ['HdmiStreamSink', 'HdmiStreamAligner']


class HdmiStreamSink(Elaboratable):
    def __init__(self, input: ImageStream, resource, modeline, pix_domain="pix", generate_clocks=True):
        self.input = input
        self.generate_clocks = generate_clocks
        self.pix_domain = pix_domain
        self.modeline = modeline
        self.resource = resource

    def elaborate(self, platform):
        m = Module()

        hdmi = m.submodules.hdmi = HdmiTx(self.resource, self.modeline, self.pix_domain, self.generate_clocks)
        m.submodules.aligner = DomainRenamer(self.pix_domain)(HdmiStreamAligner(self.input, hdmi))
        m.d.comb += hdmi.rgb.eq(RGB24(self.input.payload))

        return m


class HdmiStreamAligner(Elaboratable):
    """
    Aligns the HDMI output to the Image stream by 'slipping' data during the blanking periods until the frame is
    aligned.
    """
    def __init__(self, input: ImageStream, hdmi):
        self.hdmi = hdmi
        self.input = input

        self.allow_slip_h = ControlSignal(reset=1)
        self.allow_slip_v = ControlSignal(reset=1)
        self.slipped_v = StatusSignal(32)
        self.slipped_h = StatusSignal(32)

        self.line_cycles = StatusSignal(32)
        self.frame_cycles = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        m.submodules.debug = InflexibleSinkDebug(self.input)
        input_stream_info = m.submodules.input_stream_info = StreamInfo(stream=self.input)

        line_length_counter = Signal(32)
        was_blanking_x = Signal()
        m.d.sync += was_blanking_x.eq(self.hdmi.timing_generator.is_blanking_x)
        with m.If(~self.hdmi.timing_generator.is_blanking_x):
            m.d.sync += line_length_counter.eq(line_length_counter + 1)
        with m.If(self.hdmi.timing_generator.is_blanking_x & ~was_blanking_x):
            m.d.sync += self.line_cycles.eq(line_length_counter)
            m.d.sync += line_length_counter.eq(0)

        frame_length_counter = Signal(32)
        was_blanking_y = Signal()
        m.d.sync += was_blanking_y.eq(self.hdmi.timing_generator.is_blanking_y)
        with m.If(self.hdmi.timing_generator.active):
            m.d.sync += frame_length_counter.eq(frame_length_counter + 1)
        with m.If(self.hdmi.timing_generator.is_blanking_y & ~was_blanking_y):
            m.d.sync += self.frame_cycles.eq(frame_length_counter)
            m.d.sync += frame_length_counter.eq(0)

        with m.If(self.hdmi.timing_generator.active):
            m.d.comb += self.input.ready.eq(1)

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

        return m
