class StreamTransformer:
    def __init__(self, input_stream, output_stream, m):
        m.d.comb += input_stream.ready.eq(output_stream.ready)
        m.d.comb += output_stream.valid.eq(input_stream.valid)
        self.conditional_block = m.If(input_stream.ready & input_stream.valid)

    def __enter__(self):
        self.conditional_block.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conditional_block.__exit__(exc_type, exc_val, exc_tb)
