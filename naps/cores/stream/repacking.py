from nmigen import *
from naps import BasicStream, stream_transformer

__all__ = ["Repack12BitStream"]


class Repack12BitStream(Elaboratable):
    """Repacks a packed 12 bit little endian stream to a packed 12 bit big endian stream
    This core is probably not what you want unless you want to hand of your data to a computer.
    Then do this as your very last step because everything beyond this is pure confusion.
    """
    def __init__(self, input: BasicStream, inverse=False):
        self.input = input
        assert len(self.input.payload) % 24 == 0
        self.inverse = inverse

        self.output = self.input.clone()

    def elaborate(self, platform):
        m = Module()

        stream_transformer(self.input, self.output, m, latency=0)
        for i in range(len(self.input.payload) // 24):
            input_slice = self.input.payload[i * 24:(i + 1) * 24]
            output_slice = self.output.payload[i * 24:(i + 1) * 24]

            # (assuming the least significant bit is written right and the byte with the lowest address is the rightmost byte)
            # input:  NMLKJIHG FEDCBA98 76543210
            # output: JIHGFEDC 3210NMLK BA987654

            if not self.inverse:
                m.d.comb += output_slice[0:4].eq(input_slice[4:8])
                m.d.comb += output_slice[4:8].eq(input_slice[8:12])
                m.d.comb += output_slice[8:12].eq(input_slice[20:24])
                m.d.comb += output_slice[12:16].eq(input_slice[0:4])
                m.d.comb += output_slice[16:20].eq(input_slice[12:16])
                m.d.comb += output_slice[20:24].eq(input_slice[16:20])
            else:
                m.d.comb += output_slice[4:8].eq(input_slice[0:4])
                m.d.comb += output_slice[8:12].eq(input_slice[4:8])
                m.d.comb += output_slice[20:24].eq(input_slice[8:12])
                m.d.comb += output_slice[0:4].eq(input_slice[12:16])
                m.d.comb += output_slice[12:16].eq(input_slice[16:20])
                m.d.comb += output_slice[16:20].eq(input_slice[20:24])

        return m
