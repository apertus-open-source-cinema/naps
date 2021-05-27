from collections import defaultdict
from typing import List
from nmigen import *
from naps import Stream, DOWNWARDS, nAll, BasicStream
from . import StreamBuffer

__all__ = ["StreamTee", "StreamSplitter", "StreamCombiner"]


class StreamSplitter(Elaboratable):
    """ Routes a single N-bit stream to multiple (M) outputs which are each N/M bit wide.
    Internally uses a StreamTee.
    """

    def __init__(self, input: BasicStream, num_outputs: int):
        self.input = input
        self.num_outputs = num_outputs

        input_len = len(self.input.payload)
        self.output_len = input_len // num_outputs
        assert self.output_len * num_outputs == input_len

        self.outputs: List[BasicStream] = []
        for i in range(num_outputs):
            output = self.input.clone(name=f"output{i}")
            output.payload = Signal(self.output_len)
            self.outputs.append(output)

    def elaborate(self, platform):
        m = Module()

        tee = m.submodules.tee = StreamTee(self.input)
        for i, output in enumerate(self.outputs):
            tee_output = tee.get_output()
            m.d.comb += output.connect_upstream(tee_output)
            m.d.comb += output.payload.eq(tee_output.payload[i * self.output_len: (i + 1) * self.output_len])

        return m


class StreamTee(Elaboratable):
    """Routes a single stream input to multiple outputs (like a tee shaped piece of pipe).
    To be able to fulfil the stream contract, every output has a StreamBuffer.
    """

    def __init__(self, input: Stream):
        self.input = input
        self.outputs: List[Stream] = []
        self.m = Module()

    def get_output(self):
        n = len(self.outputs)
        output_before_buffer = self.input.clone(name=f"output{n}_before_fifo")
        self.outputs.append(output_before_buffer)
        output_fifo = StreamBuffer(output_before_buffer)
        self.m.submodules[f"output{n}_fifo"] = output_fifo
        return output_fifo.output

    def elaborate(self, platform):
        m = self.m

        m.d.comb += self.input.ready.eq(nAll(output.ready for output in self.outputs))
        for output in self.outputs:
            m.d.comb += output.valid.eq(self.input.valid & self.input.ready)
            for k in self.input.payload_signals.keys():
                u, d = self.input.payload_signals[k], output.payload_signals[k]
                m.d.comb += d.eq(u)

        return m


class StreamCombiner(Elaboratable):
    def __init__(self, *inputs: Stream, **merge_plan):

        payload_signals = defaultdict(list)
        for input in inputs:
            for k, signal in input.payload_signals.items():
                payload_signals[k].append(signal)

        payload_expressions = {}
        for k, signals in payload_signals.items():
            if "exclude_{}".format(k) in merge_plan:
                continue
            elif "merge_{}".format(k) in merge_plan:
                payload_expressions[k] = Cat(signals)
            else:
                payload_expressions[k] = signals[0]

        class CombinedStream(Stream):
            def __init__(self, name=None, src_loc_at=1):
                super().__init__(name=name, src_loc_at=1 + src_loc_at)
                for k, expr in payload_expressions.items():
                    setattr(self, k, Signal(len(expr)) @ DOWNWARDS)

        self.payload_expressions = payload_expressions

        self.inputs = inputs
        self.output = CombinedStream()

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.output.valid.eq(nAll(input.valid for input in self.inputs))
        for input in self.inputs:
            m.d.comb += input.ready.eq(self.output.ready)
        for k, expr in self.payload_expressions.items():
            m.d.comb += self.output[k].eq(expr)

        return m
