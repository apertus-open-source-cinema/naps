from nmigen import *
from naps import PacketizedStream, DOWNWARDS

__all__ = ["VariableWidthStream", "BitStuffer"]


class VariableWidthStream(PacketizedStream):
    """
    A stream that can indicate that only n bits of the payload are relevant.
    """

    def __init__(self, payload_shape, name=None, reset_width=0, src_loc_at=1):
        super().__init__(payload_shape, name, src_loc_at=1 + src_loc_at)
        self.current_width = Signal(range(len(self.payload)), reset=reset_width) @ DOWNWARDS


class BitStuffer(Elaboratable):
    """stuffs bits from a VariableWidthStream into a dense Stream"""

    def __init__(self, input: VariableWidthStream, output_width):
        self.input = input
        self.output = PacketizedStream(output_width, name="bit_stuffer_output")

    def elaborate(self, platform):
        m = Module()

        output_width = len(self.output.payload)

        shift_register = Signal(len(self.input.payload) + output_width)
        input_read = (self.input.ready & self.input.valid)
        output_write = (self.output.ready & self.output.valid)
        current_bits_in_shift_register = Signal(range(len(shift_register)))
        flush = Signal()

        with m.If(input_read & ~output_write):
            with m.If(self.input.last):
                m.d.sync += flush.eq(1)
            m.d.sync += current_bits_in_shift_register.eq(current_bits_in_shift_register + self.input.current_width)
            m.d.sync += shift_register.eq((self.input.payload << current_bits_in_shift_register) | shift_register)
        with m.Elif(~input_read & output_write):
            with m.If(flush & (current_bits_in_shift_register <= output_width)):
                m.d.sync += flush.eq(0)
                m.d.sync += current_bits_in_shift_register.eq(0)
            m.d.sync += current_bits_in_shift_register.eq(current_bits_in_shift_register - output_width)
            m.d.sync += shift_register.eq(shift_register[output_width:])
        with m.Elif(input_read & output_write):
            with m.If(self.input.last):
                m.d.sync += flush.eq(1)
            m.d.sync += current_bits_in_shift_register.eq(current_bits_in_shift_register + self.input.current_width - output_width)
            m.d.sync += shift_register.eq((self.input.payload << (current_bits_in_shift_register - output_width)) | (shift_register >> output_width))

        with m.If(flush & (current_bits_in_shift_register <= output_width)):
            m.d.comb += self.output.last.eq(1)
        m.d.comb += self.output.payload.eq(shift_register[:output_width])
        m.d.comb += self.output.valid.eq((current_bits_in_shift_register >= output_width) | flush)

        # do not accept a zero lenght packet if we are already presenting a valid output as this could
        # change the last signal of an ongoing transaction.
        with m.If((self.input.current_width == 0) & (current_bits_in_shift_register >= output_width)):
            m.d.comb += self.input.ready.eq(0)
        with m.Else():
            m.d.comb += self.input.ready.eq(((len(shift_register) - current_bits_in_shift_register) >= len(self.input.payload)) & ~self.output.last)

        return m
