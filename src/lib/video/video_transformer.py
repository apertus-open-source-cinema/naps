from typing import Tuple

from nmigen import *
from nmigen.hdl.ast import Operator

from lib.peripherals.csr_bank import StatusSignal
from lib.video.image_stream import ImageStream


class VideoTransformer(Elaboratable):
    def __init__(self, input: ImageStream, transformer_function, max_width=3000, max_height=3000):
        self.input = input
        self.max_width = max_width

        self.input_x = Signal(range(max_width))
        self.input_y = Signal(range(max_height))

        self.output_x = Signal(range(max_width))
        self.output_y = Signal(range(max_height))

        self.image_proxy = ImageProxy(self.input.payload.shape(), self.output_x, self.output_y)
        self.output_payload = transformer_function(self.output_x, self.output_y, self.image_proxy)

        self.width = StatusSignal(16, reset=self.max_width)
        self.height = StatusSignal(16, reset=max_height)

        self.delayed_cycles = StatusSignal(range(max_width * max_height))

        self.output = ImageStream(Value.cast(self.output_payload).shape(), name="video_transformer_output")

    def elaborate(self, platform):
        m = Module()

        shift_x = -min(min(x for x, y in self.image_proxy.offset_mapping.keys()), 0)
        shift_y = -min(min(y for x, y in self.image_proxy.offset_mapping.keys()), 0)

        available_pixels = {}
        needed_rows = max(y + shift_y for x, y in self.image_proxy.offset_mapping.keys())
        for y in range(needed_rows + 1):
            if y == 0:
                available_pixels[(0, y)] = self.input.payload
            else:
                memory = Memory(width=len(self.input.payload), depth=self.max_width)
                write_port = memory.write_port()
                m.submodules += write_port
                m.d.comb += write_port.addr.eq(self.input_x)
                m.d.comb += write_port.data.eq(available_pixels[0, y-1])
                m.d.comb += write_port.en.eq(1)
                read_port = memory.read_port(transparent=False)
                m.submodules += read_port
                m.d.comb += read_port.en.eq(1)
                m.d.comb += read_port.addr.eq((self.input_x + 1) % self.width)
                available_pixels[(0, y)] = Signal.like(self.input.payload)
                m.d.comb += available_pixels[(0, y)].eq(read_port.data)

            needed_pixels = max(x + shift_x for x, y in self.image_proxy.offset_mapping.keys() if y == y)
            for x in range(1, needed_pixels + 1):
                available_pixels[(x, y)] = Signal.like(self.input.payload)
                m.d.sync += available_pixels[(x, y)].eq(available_pixels[(x - 1, y)])

        read_input = self.input.ready & self.input.valid
        write_output = self.output.ready & self.output.valid

        with m.If(read_input):
            with m.If(~self.input.line_last):
                m.d.sync += self.input_x.eq(self.input_x + 1)
            with m.Else():
                m.d.sync += self.input_x.eq(0)
                m.d.sync += self.width.eq(self.input_x + 1)
                with m.If(~self.input.frame_last):
                    m.d.sync += self.input_y.eq(self.input_y + 1)
                with m.Else():
                    m.d.sync += self.input_y.eq(0)
                    m.d.sync += self.height.eq(self.input_y + 1)

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
            with m.If((self.output_x - x >= 0) & (self.output_x - x < self.width) &
                      (self.output_y - y >= 0) & (self.output_y - y < self.height)):
                m.d.comb += signal.eq(available_pixels[x + shift_x, y + shift_y])
        m.d.comb += self.output.payload.eq(self.output_payload)
        
        with m.If(read_input & ~write_output):
            m.d.sync += self.delayed_cycles.eq(self.delayed_cycles + 1)
        with m.Elif(~read_input & write_output):
            m.d.sync += self.delayed_cycles.eq(self.delayed_cycles - 1)

        with m.If(self.delayed_cycles <= shift_x + (self.width * shift_y)):
            m.d.comb += self.input.ready.eq(1)
        with m.If(self.delayed_cycles >= shift_x + (self.width * shift_y)):
            m.d.comb += self.output.valid.eq(1)

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
            "the value {!r} is not allowed here. only terms that are {!r} +/- a constant are allowed".format(expr,
                                                                                                             allowed_variable))
        if isinstance(expr, Signal):
            if not expr is allowed_variable:
                raise e
            return 0
        elif isinstance(expr, Operator):
            if not expr.operator in ("+", "-"):
                raise e
            if (not len(expr.operands) == 2) and (expr.operands[0] is allowed_variable) and (
            isinstance(expr.operands[1], Const)):
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
