from math import ceil
from nmigen import *
from naps import BasicStream, PacketizedStream, ControlSignal, StatusSignal

__all__ = ['Ft60xLegalizer']


class Ft60xLegalizer(Elaboratable):
    def __init__(self, input: PacketizedStream, packet_len):
        self.input = input
        self.output = BasicStream(input.payload.shape())

        # we calculate everything in bytes to make it easier to reason about
        buffer_size = 2048 * 4
        blanking = buffer_size
        aligned_len = ceil((packet_len + blanking) / buffer_size) * buffer_size
        print("ft60x paddnig:", (aligned_len - packet_len), (aligned_len - packet_len) // 4)

        self.padding = ControlSignal(16, reset=(aligned_len - packet_len) // 4)
        self.frame_len = StatusSignal(32)
        self.frame_len_changed = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        padding_ctr = Signal.like(self.padding)
        frame_len_ctr = Signal.like(self.frame_len)

        input_transaction = self.input.ready & self.input.valid
        with m.FSM():
            with m.State("ACTIVE"):
                m.d.comb += self.input.ready.eq(self.output.ready)
                m.d.comb += self.output.valid.eq(self.input.valid)
                with m.If(self.input.payload == 0):  # we disallow the transfer of 0 to ease the alignment detection TODO: this only really works for 8 bit this way
                    m.d.comb += self.output.payload.eq(1)
                with m.Else():
                    m.d.comb += self.output.payload.eq(self.input.payload)
                with m.If(input_transaction):
                    m.d.sync += frame_len_ctr.eq(frame_len_ctr + 1)
                with m.If(self.input.last & input_transaction):
                    m.next = "PADDING"
                    m.d.sync += padding_ctr.eq(0)
            with m.State("PADDING"):
                m.d.comb += self.output.valid.eq(1)
                m.d.comb += self.input.ready.eq(0)
                m.d.comb += self.output.payload.eq(0)
                with m.If(self.output.ready):
                    with m.If(padding_ctr < self.padding - 1):
                        m.d.sync += padding_ctr.eq(padding_ctr + 1)
                        m.d.sync += frame_len_ctr.eq(frame_len_ctr + 1)
                    with m.Else():
                        m.next = "ACTIVE"
                        m.d.sync += self.frame_len.eq(frame_len_ctr + 1)
                        with m.If(self.frame_len != frame_len_ctr + 1):
                            m.d.sync += self.frame_len_changed.eq(self.frame_len_changed + 1)
                        m.d.sync += frame_len_ctr.eq(0)
        return m
