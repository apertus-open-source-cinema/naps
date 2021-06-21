from nmigen import *
from naps import iterator_with_if_elif
from ..tmds import tmds_control_tokens



class TmdsDecoder(Elaboratable):
    """
    Decodes tmds signals.
    """
    def __init__(self, input: Signal):
        self.input = input

        self.data_enable = Signal()
        self.data = Signal(8)
        self.control = Signal(2)

    def elaborate(self, platform):
        m = Module()

        for cond, (i, token) in iterator_with_if_elif(enumerate(tmds_control_tokens), m):
            with cond(self.input == token):
                m.d.comb += self.data_enable.eq(0)
                m.d.comb += self.control.eq(i)
        with m.Else():
            inverted = Signal(8)
            m.d.comb += inverted.eq(Mux(self.input[9], ~self.input[0:8], self.input[0:8]))
            xored = Signal(8)
            m.d.comb += xored[0].eq(inverted[0])
            m.d.comb += xored[1].eq(inverted[1] ^ inverted[0])
            m.d.comb += xored[2].eq(inverted[2] ^ inverted[1])
            m.d.comb += xored[3].eq(inverted[3] ^ inverted[2])
            m.d.comb += xored[4].eq(inverted[4] ^ inverted[3])
            m.d.comb += xored[5].eq(inverted[5] ^ inverted[4])
            m.d.comb += xored[6].eq(inverted[6] ^ inverted[5])
            m.d.comb += xored[7].eq(inverted[7] ^ inverted[6])
            with m.If(self.input[8]):  # XOR encoding
                m.d.comb += self.data.eq(xored)
            with m.Else():  # XNOR encoding
                m.d.comb += self.data.eq(Cat(xored[0], ~xored[1:]))
            m.d.comb += self.data_enable.eq(1)

        return m
