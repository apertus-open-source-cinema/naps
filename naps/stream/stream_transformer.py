from amaranth import *
from amaranth.lib import wiring, stream

__all__ = ["stream_transformer"]

from naps import out_of_band_signals


def stream_transformer(m: Module, input_stream: stream.Interface, output_stream: stream.Interface, *, latency: int):
    """
    A utility to help you to write fixed latency stream ip that converts one input word to one output word.

    :warning:
    You have to make sure that you only sample the input when ready and valid of it are high for transformers with latency.
    otherwise you are not going to comply to the stream contract. In this case you MUST place a StreamBuffer after your core.

    @param input_stream: the input stream
    @param output_stream: the output stream
    @param m: an amaranth HDL Module
    @param latency: the latency of the transform data path in cycles
    """
    if latency == 0:
        m.d.comb += [
            output_stream.valid.eq(input_stream.valid),
            input_stream.valid.eq(output_stream.valid)
        ]
        m.d.comb += [
            o.eq(i) for o, i in zip(out_of_band_signals(output_stream.p), out_of_band_signals(input_stream.p))
        ]
        return input_stream.ready & input_stream.valid

    elif latency == 1:
        input_transaction = input_stream.ready & input_stream.valid
        output_transaction = output_stream.ready & output_stream.valid

        with m.If(input_transaction):
            m.d.sync += [
                o.eq(i) for o, i in zip(out_of_band_signals(output_stream.p), out_of_band_signals(input_stream.p))
            ]

        output_produce = Signal()
        m.d.sync += output_produce.eq(input_transaction)

        has_output = Signal()
        with m.If(has_output | output_produce):
            m.d.comb += output_stream.valid.eq(1)
        m.d.sync += has_output.eq(has_output + output_produce - output_transaction > 0)
        m.d.comb += input_stream.ready.eq(output_stream.ready | (~has_output & ~output_produce))
        return input_transaction
    else:
        raise NotImplementedError()
