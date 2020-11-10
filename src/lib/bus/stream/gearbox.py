from nmigen import *

from lib.bus.stream.stream import BasicStream
from lib.data_structure.bundle import DOWNWARDS


class StreamResizer(Elaboratable):
    """Simply resizing a Stream by truncating or zero extending the payload"""
    def __init__(self, input: BasicStream, target_width):
        self.input = input
        self.output = input.clone(name="resizer_output")
        self.output.payload = Signal(target_width) @ DOWNWARDS

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.input.connect_downstream(self.output)
        return m


class StreamGearbox(Elaboratable):
    """Resize a Stream by 'Gearing' it up / down (changing the word rate)"""
    def __init__(self, input: BasicStream, target_width):
        self.input = input
        self.output = input.clone(name="gearbox_output")
        self.output.payload = Signal(target_width) @ DOWNWARDS
        self.counter = Signal(32)

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.counter.eq(self.counter + 1)

        input_width = len(self.input.payload)
        output_width = len(self.output.payload)

        if input_width > output_width:
            reg_width = input_width + output_width
        else:
            reg_width = (output_width + (input_width - 1)) // input_width * input_width

        shift_register = Signal(reg_width)
        input_read = (self.input.ready & self.input.valid)
        output_write = (self.output.ready & self.output.valid)
        current_bits_in_shift_register = Signal(range(len(shift_register)))

        with m.If(input_read & ~output_write):
            m.d.sync += current_bits_in_shift_register.eq(current_bits_in_shift_register + input_width)
            m.d.sync += shift_register.eq(shift_register | (self.input.payload << current_bits_in_shift_register))

        with m.Elif(~input_read & output_write):
            m.d.sync += current_bits_in_shift_register.eq(current_bits_in_shift_register - output_width)
            m.d.sync += shift_register.eq(shift_register[output_width:])

        with m.Elif(input_read & output_write):
            m.d.sync += current_bits_in_shift_register.eq(current_bits_in_shift_register + input_width - output_width)
            m.d.sync += shift_register.eq((shift_register >> output_width) | (self.input.payload << (current_bits_in_shift_register - output_width)))


        m.d.comb += self.output.payload.eq(shift_register[:output_width])
        m.d.comb += self.output.valid.eq(current_bits_in_shift_register >= output_width)
        m.d.comb += self.input.ready.eq((len(shift_register) - current_bits_in_shift_register) >= input_width)

        return m
