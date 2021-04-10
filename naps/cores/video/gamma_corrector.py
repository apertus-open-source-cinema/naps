from nmigen import *

from naps import ControlSignal, stream_transformer
from . import ImageStream

__all__ = ["TableGammaCorrector"]


class TableGammaCorrector(Elaboratable):
    """Apply gamma correction to a monochrome image using a pre-computed lookup table"""
    def __init__(self, input: ImageStream, gamma: float):
        self.input = input
        self.bpp = len(input.payload)
        self.output = ImageStream(self.bpp)

        self.gamma = gamma

    def elaborate(self, platform):
        m = Module()

        stream_transformer(self.input, self.output, m, latency=1)
        input_transaction = self.input.ready & self.input.valid

        # compute the gamma lookup table with the formula
        # out = in ^ gamma, where in and out are 0-1 and ^ is exponentiation
        max_pix = 2**self.bpp - 1
        lut = list(int(max_pix*((v/max_pix)**self.gamma)+0.5) for v in range(max_pix+1))

        lut_mem = Memory(width=self.bpp, depth=2**self.bpp, init=lut)
        lut_port = m.submodules.lut_port = lut_mem.read_port(domain="sync", transparent=False)

        m.d.comb += lut_port.en.eq(input_transaction)
        m.d.comb += lut_port.addr.eq(self.input.payload)
        m.d.comb += self.output.payload.eq(lut_port.data)

        return m
