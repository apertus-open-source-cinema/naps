from typing import List

from nmigen import *

from lib.bus.stream.fifo import BufferedSyncStreamFIFO
from lib.bus.stream.stream import BasicStream
from util.nmigen_misc import nAll


class StreamTransformer:
    """A contextmanager that helps writing simple cores that transform one input word to one output word only using combinatorial logic.

    All the combinatorial computation that mutate the state of the payload signals must not happen inside this context manager.
    (because that would violate the stream contract invariants.) You should use the context manager only to mutate interior state
    of your Core (e.g. a transaction counter).
    """
    def __init__(self, input_stream, output_stream, m):
        m.d.comb += input_stream.ready.eq(output_stream.ready)
        m.d.comb += output_stream.valid.eq(input_stream.valid)
        self.conditional_block = m.If(input_stream.ready & input_stream.valid)

    def __enter__(self):
        self.conditional_block.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conditional_block.__exit__(exc_type, exc_val, exc_tb)


class MultiStreamTransformer:
    """A contextmanager that helps writing cores that transform n input streams to n output streams while transforming
    one input stream to one output word per stream only using combinatorial logic. This contextmanager takes care of all
    the inter-stream synchronization. To be able to fulfil the stream output contract, this core has a FIFO on all its outputs.

    All the combinatorial computation that mutate the state of the payload signals must not happen inside this context manager.
    (because that would violate the stream contract invariants.) You should use the context manager only to mutate interior state
    of your Core (e.g. a transaction counter).
    """

    def __init__(self, input_streams: List[BasicStream], output_streams: List[BasicStream], m):
        output_streams_before_fifo = [s.clone() for s in output_streams]
        # TODO: 1 deep FIFOs would suffice here but that is not verifiable due to a yosys bug:
        #       https://github.com/YosysHQ/yosys/issues/2577
        output_stream_fifos = [BufferedSyncStreamFIFO(s, 2) for s in output_streams_before_fifo]
        for a, b in zip(output_streams, output_stream_fifos):
            m.d.comb += a.connect_upstream(b)

        output_ready = Signal()
        m.d.comb += output_ready.eq(nAll(s.ready for s in output_streams_before_fifo))
        output_valid = Signal()
        for s in output_streams_before_fifo:
            m.d.comb += s.valid.eq(output_valid)
        input_valid = Signal()
        m.d.comb += input_valid.eq(nAll(s.valid for s in input_streams))
        input_ready = Signal()
        for s in input_streams:
            m.d.comb += s.ready.eq(input_ready)

        m.d.comb += output_valid.eq(output_ready & input_valid)
        m.d.comb += input_ready.eq(output_ready)

        self.conditional_block = m.If(output_ready & output_valid)

    def __enter__(self):
        self.conditional_block.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conditional_block.__exit__(exc_type, exc_val, exc_tb)
