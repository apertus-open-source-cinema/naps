from nmigen import *

from lib.bus.stream.debug import StreamInfo
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

    def elaborate(self, platform):
        m = Module()

        m.submodules.input_stream_info = StreamInfo(self.input)
        m.submodules.output_stream_info = StreamInfo(self.output)

        input_width = len(self.input.payload)
        output_width = len(self.output.payload)

        shift_register = Signal(input_width + output_width - 1)  # TODO: this is wrong!
        input_read = (self.input.ready & self.input.valid)
        output_write = (self.output.ready & self.output.valid)
        current_bits_in_shift_register = Signal(range(len(shift_register)))

        last_shift_register = Signal(input_width + output_width - 1)  # this is a evil hack
        last_payload = (1 << (input_width - 1))

        with m.If(input_read & ~output_write):
            m.d.sync += current_bits_in_shift_register.eq(current_bits_in_shift_register + input_width)
            m.d.sync += shift_register.eq(shift_register | (self.input.payload << current_bits_in_shift_register))
            m.d.sync += last_shift_register.eq(last_shift_register | (last_payload << current_bits_in_shift_register))

        with m.Elif(~input_read & output_write):
            m.d.sync += current_bits_in_shift_register.eq(current_bits_in_shift_register - output_width)
            m.d.sync += shift_register.eq(shift_register[output_width:])
            m.d.sync += last_shift_register.eq(last_shift_register[output_width:])

        with m.Elif(input_read & output_write):
            m.d.sync += current_bits_in_shift_register.eq(current_bits_in_shift_register + input_width - output_width)
            m.d.sync += shift_register.eq((shift_register >> output_width) | (self.input.payload << (current_bits_in_shift_register - output_width)))
            m.d.sync += last_shift_register.eq((last_shift_register >> output_width) | (last_payload << (current_bits_in_shift_register - output_width)))

        m.d.comb += self.output.payload.eq(shift_register[:output_width])
        m.d.comb += self.output.valid.eq(current_bits_in_shift_register >= output_width)
        m.d.comb += self.input.ready.eq((len(shift_register) - current_bits_in_shift_register) >= input_width)
        
        payload_signals_in_current_word = {k: Signal.like(v, name="{}_in_current_word".format(k))
                                           for k, v in self.input.out_of_band_signals.items()}

        with m.If(input_read):
            m.d.sync += [payload_signals_in_current_word[k].eq(getattr(self.input, k))
                         for k in payload_signals_in_current_word.keys()]

        last = Signal()
        m.d.comb += last.eq(last_shift_register[:output_width] != 0)

        for k in payload_signals_in_current_word.keys():
            if k.endswith("last"):
                with m.If(last):
                    m.d.comb += getattr(self.output, k).eq(payload_signals_in_current_word[k])
            else:
                m.d.comb += getattr(self.output, k).eq(payload_signals_in_current_word[k])

        return m
