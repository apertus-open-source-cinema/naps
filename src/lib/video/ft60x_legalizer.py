from math import ceil

from nmigen import *

from lib.bus.stream.stream import BasicStream
from lib.peripherals.csr_bank import ControlSignal
from lib.video.image_stream import ImageStream


class Ft60xLegalizer(Elaboratable):
    def __init__(self, input: ImageStream, width, height, bit_depth):
        self.input = input
        self.output = BasicStream(input.payload.shape())

        buffer_size = 2048
        blanking = buffer_size
        frame_len = int(width * height * bit_depth / 8)
        aligned_len = ceil((frame_len + blanking) / buffer_size) * buffer_size
        self.padding = ControlSignal(16, reset=aligned_len - frame_len)

    def elaborate(self, platform):
        m = Module()

        padding_ctr = Signal.like(self.padding)

        input_transaction = self.input.ready & self.input.valid
        with m.FSM():
            with m.State("ACTIVE"):
                m.d.comb += self.input.ready.eq(self.output.ready)
                m.d.comb += self.output.valid.eq(self.input.valid)
                m.d.comb += self.output.payload.eq(self.input.payload)
                with m.If(self.input.frame_last & input_transaction):
                    m.next = "PADDING"
                    m.d.sync += padding_ctr.eq(0)
            with m.State("PADDING"):
                m.d.comb += self.output.valid.eq(1)
                m.d.comb += self.input.ready.eq(0)
                m.d.comb += self.output.payload.eq(0)
                with m.If(self.output.ready):
                    with m.If(padding_ctr < self.padding):
                        m.d.sync += padding_ctr.eq(padding_ctr + 1)
                    with m.Else():
                        m.next = "ACTIVE"

        return m
