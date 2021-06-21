from nmigen import *
from naps import BasicStream, DOWNWARDS
from . import StreamInfo

__all__ = ["StreamResizer", "StreamGearbox", "SimpleStreamGearbox"]


class StreamResizer(Elaboratable):
    """Simply resizing a Stream by truncating or zero extending the payload"""

    def __init__(self, input: BasicStream, target_width, upper_bits=False):
        self.input = input
        self.output = input.clone(name="resizer_output")
        self.output.payload = Signal(target_width) @ DOWNWARDS
        self.upper_bits = upper_bits

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.output.connect_upstream(self.input, exclude=["payload"])
        if not self.upper_bits:
            m.d.comb += self.output.payload.eq(self.input.payload)
        else:
            m.d.comb += self.output.payload.eq(self.input.payload[-len(self.output.payload):])
        return m


class StreamGearbox(Elaboratable):
    """Resize a Stream by 'Gearing' it up / down (changing the word rate)"""
    # TODO: add flushing on first & last
    # (maybe add valid logic wit sub word granularity?)
    # do we need streams with more granular enables (also for more than 1 px / cycle throughput blocks?)

    def __init__(self, input: BasicStream, target_width):
        self.input = input
        self.output = input.clone(name="gearbox_output")
        self.output.payload = Signal(target_width) @ DOWNWARDS

    def elaborate(self, platform):
        m = Module()

        input_width = len(self.input.payload)
        output_width = len(self.output.payload)

        shift_register = Signal(input_width + output_width + min(input_width, output_width))
        input_read = (self.input.ready & self.input.valid)
        output_write = (self.output.ready & self.output.valid)
        current_bits_in_shift_register = Signal(range(len(shift_register) + 1))

        for k, v in self.input.out_of_band_signals.items():
            if not (k == "payload" or (k.endswith("last") and len(v) == 1) or (k.endswith("first") and len(v) == 1)):
                raise ValueError("payload signal {} of input has unknown role. dont know what do do with it")

        last_first_shift_registers = {k: Signal.like(shift_register, name="{}_shift_register".format(k))
                                for k, v in self.input.out_of_band_signals.items() if (k.endswith("last") or k.endswith("first"))}

        shift_registers = [(shift_register, self.input.payload)]
        shift_registers += [(reg, (self.input[k] << ((input_width - 1) if k.endswith("last") else 0)))
                            for k, reg in last_first_shift_registers.items()]

        with m.If(input_read & ~output_write):
            m.d.sync += current_bits_in_shift_register.eq(current_bits_in_shift_register + input_width)
            for reg, payload in shift_registers:
                m.d.sync += reg.eq((payload << current_bits_in_shift_register) | reg)
        with m.Elif(~input_read & output_write):
            m.d.sync += current_bits_in_shift_register.eq(current_bits_in_shift_register - output_width)
            for reg, payload in shift_registers:
                m.d.sync += reg.eq(reg >> output_width)
        with m.Elif(input_read & output_write):
            m.d.sync += current_bits_in_shift_register.eq(current_bits_in_shift_register + input_width - output_width)
            for reg, payload in shift_registers:
                m.d.sync += reg.eq((payload << (current_bits_in_shift_register - output_width)) | (reg >> output_width))

        m.d.comb += self.output.payload.eq(shift_register[:output_width])
        m.d.comb += self.output.valid.eq(current_bits_in_shift_register >= output_width)
        m.d.comb += self.input.ready.eq((len(shift_register) - current_bits_in_shift_register) >= input_width)

        m.d.comb += [self.output[k].eq(reg[:output_width] != 0) for k, reg in last_first_shift_registers.items()]

        return m


class SimpleStreamGearbox(Elaboratable):
    def __init__(self, input: BasicStream, target_width):
        self.input = input
        self.output = input.clone(name="gearbox_output")
        self.output.payload = Signal(target_width) @ DOWNWARDS

        self.input_width = len(self.input.payload)
        self.output_width = target_width
        self.division_factor = self.input_width / target_width

        assert target_width < self.input_width
        assert self.division_factor % 1 == 0
        self.division_factor = int(self.division_factor)

    def elaborate(self, platform):
        m = Module()

        input_read = (self.input.ready & self.input.valid)
        output_write = (self.output.ready & self.output.valid)

        for k, v in self.input.out_of_band_signals.items():
            if not (k == "payload" or (k.endswith("last") and len(v) == 1)):
                raise ValueError("payload signal {} of input has unknown role. dont know what do do with it")

        last_signals = {
            k: Signal(1, name="{}_store".format(k))
            for k, v in self.input.out_of_band_signals.items()
            if k.endswith("last")
        }

        reg = Signal(self.input_width - self.output_width)
        state = Signal(range(self.division_factor))
        with m.If(state == 0):
            m.d.comb += self.input.ready.eq(self.output.ready)
            m.d.comb += self.output.valid.eq(self.input.valid)
            m.d.comb += self.output.payload.eq(self.input.payload[:self.output_width])
            with m.If(input_read):
                m.d.sync += reg.eq(self.input.payload[self.output_width:])
                m.d.sync += state.eq(state + 1)
                for k, v in last_signals.items():
                    m.d.sync += v.eq(self.input[k])
        with m.Else():
            m.d.comb += self.output.payload.eq(reg)
            m.d.comb += self.output.valid.eq(1)
            m.d.comb += self.input.ready.eq(0)
            with m.If(output_write):
                m.d.sync += reg.eq(reg[self.output_width:])
                m.d.sync += state.eq(state + 1)
            with m.If(state == self.division_factor - 1):
                for k, v in last_signals.items():
                    m.d.comb += self.output[k].eq(v)

        return m
