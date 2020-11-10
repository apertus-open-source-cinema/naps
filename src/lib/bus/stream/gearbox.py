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

        shift_register = Signal(input_width + output_width)
        input_read = (self.input.ready & self.input.valid)
        output_write = (self.output.ready & self.output.valid)
        current_bits_in_shift_register = Signal(range(len(shift_register)))

        for k in self.input.out_of_band_signals.keys():
            if not (k == "payload" or k.endswith("last")):
                raise ValueError("payload signal {} of input has unknown role. dont know what do do with it")

        last_shift_registers = {k: Signal.like(shift_register, name="{}_shift_register".format(k))
                                for k, v in self.input.out_of_band_signals.items() if k.endswith("last")}

        shift_registers = [(shift_register, self.input.payload)]
        shift_registers += [(reg, (getattr(self.input, k) << (input_width - 1))) for k, reg in last_shift_registers.items()]

        with m.If(input_read & ~output_write):
            m.d.sync += current_bits_in_shift_register.eq(current_bits_in_shift_register + input_width)
            for reg, payload in shift_registers:
                m.d.sync += reg.eq((payload << current_bits_in_shift_register) | reg)
        with m.Elif(~input_read & output_write):
            m.d.sync += current_bits_in_shift_register.eq(current_bits_in_shift_register - output_width)
            for reg, payload in shift_registers:
                m.d.sync += reg.eq(reg[output_width:])
        with m.Elif(input_read & output_write):
            m.d.sync += current_bits_in_shift_register.eq(current_bits_in_shift_register + input_width - output_width)
            for reg, payload in shift_registers:
                m.d.sync += reg.eq((payload << (current_bits_in_shift_register - output_width)) | (reg >> output_width))

        m.d.comb += self.output.payload.eq(shift_register[:output_width])
        m.d.comb += self.output.valid.eq(current_bits_in_shift_register >= output_width)
        m.d.comb += self.input.ready.eq((len(shift_register) - current_bits_in_shift_register) >= input_width)

        m.d.comb += [getattr(self.output, k).eq(reg[:output_width] != 0) for k, reg in last_shift_registers.items()]

        return m
