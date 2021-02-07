from collections import defaultdict
from typing import List

from nmigen import *

from lib.bus.stream.fifo import BufferedSyncStreamFIFO
from lib.bus.stream.stream import Stream, DOWNWARDS
from util.nmigen_misc import nAll


class StreamTee(Elaboratable):
    """Routes a single stream input to multiple outputs (like a tee shaped piece of pipe).
    To be able to fulfil the stream contract, every output has a 1 deep fifo.
    """

    def __init__(self, input: Stream):
        self.input = input
        self.outputs: List[Stream] = []
        self.m = Module()

    def get_output(self):
        n = len(self.outputs)
        output_before_fifo = self.input.clone(name=f"output{n}_before_fifo")
        self.outputs.append(output_before_fifo)
        output_fifo = BufferedSyncStreamFIFO(output_before_fifo, 2, output_stream_name=f"output{n}_fifo_out")
        # TODO: a 1 deep fifo would suffice here but that is not verifiable due to a yosys bug:
        #       https://github.com/YosysHQ/yosys/issues/2577
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
            m.d.comb += getattr(self.output, k).eq(expr)

        return m


class StreamHandshakeTie(Elaboratable):
    """Takes N streams as Input and outputs N streams. The streams are then """

    def __init__(self):
        pass

    def elaborate(self, platform):
        m = Module()



        return m