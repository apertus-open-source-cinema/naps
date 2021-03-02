from typing import Tuple
from nmigen import *
from nmigen.hdl.ast import Operator
from naps import StatusSignal
from . import ImageStream

__all__ = ["ImageConvoluter"]


class ImageConvoluter(Elaboratable):
    def __init__(self, input: ImageStream, transformer_function, width, height):
        self.input = input

        self.input_x = Signal(range(width))
        self.input_y = Signal(range(height))

        self.output_x = Signal(range(width))
        self.output_y = Signal(range(height))

        self.image_proxy = ImageProxy(self.input.payload.shape(), self.output_x, self.output_y)
        self.output_payload = transformer_function(self.output_x, self.output_y, self.image_proxy)
        self.shift_x = -min([x for x, y in self.image_proxy.offset_mapping.keys()] + [0])
        self.shift_y = -min([y for x, y in self.image_proxy.offset_mapping.keys()] + [0])

        self.width = width
        self.height = height

        self.delay_needed = self.shift_x + (width * self.shift_y)
        self.delayed_cycles = StatusSignal(range(self.delay_needed))

        self.output = ImageStream(Value.cast(self.output_payload).shape(), name="image_convoluter_output")

    def elaborate(self, platform):
        m = Module()

        read_input = self.input.ready & self.input.valid
        write_output = self.output.ready & self.output.valid

        available_pixels = {}
        if len(self.image_proxy.offset_mapping.keys()) > 0:
            needed_rows = max(y + self.shift_y for x, y in self.image_proxy.offset_mapping.keys())
            for y in range(needed_rows + 1):
                if y == 0:
                    available_pixels[(0, y)] = self.input.payload
                else:
                    memory = Memory(width=len(self.input.payload), depth=self.width)
                    write_port = memory.write_port()
                    m.submodules += write_port
                    with m.If(read_input):
                        m.d.comb += write_port.addr.eq(self.input_x)
                        m.d.comb += write_port.data.eq(available_pixels[0, y-1])
                        m.d.comb += write_port.en.eq(1)
                    read_port = memory.read_port(transparent=False)
                    m.submodules += read_port
                    m.d.comb += read_port.en.eq(1)
                    with m.If(read_input):
                        m.d.comb += read_port.addr.eq((self.input_x + 1) % self.width)
                    with m.Else():
                        m.d.comb += read_port.addr.eq(self.input_x)
                    available_pixels[(0, y)] = Signal.like(self.input.payload)
                    m.d.comb += available_pixels[(0, y)].eq(read_port.data)

                needed_pixels = max(x + self.shift_x for x, y in self.image_proxy.offset_mapping.keys() if y == y)
                for x in range(1, needed_pixels + 1):
                    available_pixels[(x, y)] = Signal.like(self.input.payload)
                    with m.If(read_input):
                        m.d.sync += available_pixels[(x, y)].eq(available_pixels[(x - 1, y)])

        with m.If(read_input):
            with m.If(~self.input.line_last):
                m.d.sync += self.input_x.eq(self.input_x + 1)
            with m.Else():
                m.d.sync += self.input_x.eq(0)
                with m.If(~self.input.frame_last):
                    m.d.sync += self.input_y.eq(self.input_y + 1)
                with m.Else():
                    m.d.sync += self.input_y.eq(0)

        with m.If(write_output):
            with m.If(self.output_x < self.width - 1):
                m.d.sync += self.output_x.eq(self.output_x + 1)
            with m.Else():
                m.d.sync += self.output_x.eq(0)
                m.d.comb += self.output.line_last.eq(1)
                with m.If(self.output_y < self.height - 1):
                    m.d.sync += self.output_y.eq(self.output_y + 1)
                with m.Else():
                    m.d.sync += self.output_y.eq(0)
                    m.d.comb += self.output.frame_last.eq(1)
        for (x, y), signal in self.image_proxy.offset_mapping.items():
            m.d.comb += signal.eq(available_pixels[x + self.shift_x, y + self.shift_y])
        m.d.comb += self.output.payload.eq(self.output_payload)
        
        with m.If(read_input & ~write_output):
            m.d.sync += self.delayed_cycles.eq(self.delayed_cycles + 1)
        with m.Elif(~read_input & write_output):
            m.d.sync += self.delayed_cycles.eq(self.delayed_cycles - 1)

        with m.If(self.delayed_cycles < self.delay_needed):
            m.d.comb += self.input.ready.eq(1)
        with m.Elif(self.delayed_cycles > self.delay_needed):
            m.d.comb += self.output.valid.eq(1)
        with m.Else():
            m.d.comb += self.output.valid.eq(self.input.valid)
            m.d.comb += self.input.ready.eq(self.output.ready)

        return m


class ImageProxy:
    def __init__(self, shape, x_signal, y_signal):
        self.y_signal = y_signal
        self.x_signal = x_signal
        self.shape = shape
        self.offset_mapping = {}

    @classmethod
    def _offset_from_expression(cls, expr, allowed_variable):
        e = ValueError(
            "the value {!r} is not allowed here. only terms that are {!r} +/- a constant are allowed"
                .format(expr, allowed_variable))
        if isinstance(expr, Signal):
            if not expr is allowed_variable:
                raise e
            return 0
        elif isinstance(expr, Operator):
            if not expr.operator in ("+", "-"):
                raise e
            if (not len(expr.operands) == 2) and (expr.operands[0] is allowed_variable) \
                    and (isinstance(expr.operands[1], Const)):
                raise e
            return expr.operands[1].value * (-1 if expr.operator == "-" else 1)
        else:
            raise e

    def __getitem__(self, item):
        assert isinstance(item, Tuple) and len(item) == 2
        offset = -self._offset_from_expression(item[0], self.x_signal), \
                 -self._offset_from_expression(item[1], self.y_signal)

        if offset not in self.offset_mapping:
            self.offset_mapping[offset] = Signal(self.shape)
        return self.offset_mapping[offset]
