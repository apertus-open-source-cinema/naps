from collections import defaultdict
from functools import reduce
from typing import List

from nmigen import *

from lib.bus.stream.stream import Stream, DOWNWARDS


class StreamSplitter(Elaboratable):
    """routes a single stream input to multiple outputs"""

    def __init__(self, input: Stream):
        self.input = input
        self.outputs: List[Stream] = []

    def get_output(self):
        output = self.input.clone(name="tee_output_{}".format(len(self.outputs)))
        self.outputs.append(output)
        return output

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.input.ready.eq(reduce(lambda a, b: a & b, (output.ready for output in self.outputs)))
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

        m.d.comb += self.output.valid.eq(reduce(lambda a, b: a & b, (input.valid for input in self.inputs)))
        for input in self.inputs:
            m.d.comb += input.ready.eq(self.output.ready)
        for k, expr in self.payload_expressions.items():
            m.d.comb += getattr(self.output, k).eq(expr)

        return m
