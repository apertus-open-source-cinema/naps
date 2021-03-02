from nmigen import *

__all__ = ["ISerdes8"]


class ISerdes8(Elaboratable):
    def __init__(self, input, ddr_domain, word_domain, invert=False):
        self.input = input
        self.output = Signal(8)
        self.bitslip = Signal()

        self.invert = invert
        self.ddr_domain = ddr_domain
        self.word_domain = word_domain

    def elaborate(self, platform):
        m = Module()

        iddr_output = Signal(8)
        m.d.comb += self.output.eq(iddr_output ^ Repl(self.invert, 8))
        m.submodules.iddr = Instance(
            "IDDRX4B",

            i_D=self.input,
            i_ECLK=ClockSignal(self.ddr_domain),
            i_SCLK=ClockSignal(self.word_domain),
            i_RST=ResetSignal(self.word_domain),
            i_ALIGNWD=self.bitslip,

            o_Q0=iddr_output[7],
            o_Q1=iddr_output[6],
            o_Q2=iddr_output[5],
            o_Q3=iddr_output[4],
            o_Q4=iddr_output[3],
            o_Q5=iddr_output[2],
            o_Q6=iddr_output[1],
            o_Q7=iddr_output[0],
        )

        return m