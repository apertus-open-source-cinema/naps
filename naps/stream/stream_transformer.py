from nmigen import *
from naps.stream import BasicStream

__all__ = ["stream_transformer"]


def stream_transformer(input_stream: BasicStream, output_stream: BasicStream, m: Module, *, latency: int, handle_out_of_band=True, allow_partial_out_of_band=False):
    """
    A utility to help you writing fixed latency stream ip that converts one input word to one output word.

    :warning:
    You have to make sure that you only sample the input when ready and valid of it are high for transformers with latency
    otherwise you are not going to comply to the stream contract. In this case you MUST place a StreamBuffer after your core.

    @param handle_out_of_band: determines if this core should connect the out of bands signals or if it is done manually
    @param allow_partial_out_of_band: allow the out of band signals of the streams to differ
    @param input_stream: the input stream
    @param output_stream: the output stream
    @param m: a nmigen Module
    @param latency: the latency of the transform data path in cycles
    """
    if latency == 0:
        m.d.comb += output_stream.connect_upstream(input_stream, only=["ready", "valid"])
        if handle_out_of_band:
            if not allow_partial_out_of_band:
                assert list(input_stream.out_of_band_signals.keys()) == list(output_stream.out_of_band_signals.keys())
            for k in input_stream.out_of_band_signals.keys():
                if k in output_stream.out_of_band_signals:
                    m.d.comb += output_stream[k].eq(input_stream[k])

    elif latency == 1:
        input_transaction = input_stream.ready & input_stream.valid
        output_transaction = output_stream.ready & output_stream.valid

        with m.If(input_transaction):
            if handle_out_of_band:
                if not allow_partial_out_of_band:
                    assert list(input_stream.out_of_band_signals.keys()) == list(output_stream.out_of_band_signals.keys())
                for k in input_stream.out_of_band_signals.keys():
                    if k in output_stream.out_of_band_signals:
                        m.d.sync += output_stream[k].eq(input_stream[k])

        output_produce = Signal()
        m.d.sync += output_produce.eq(input_transaction)

        has_output = Signal()
        with m.If(has_output | output_produce):
            m.d.comb += output_stream.valid.eq(1)
        m.d.sync += has_output.eq(has_output + output_produce - output_transaction > 0)
        m.d.comb += input_stream.ready.eq(output_stream.ready | (~has_output & ~output_produce))

    else:
        raise NotImplementedError()