from nmigen import Elaboratable, Signal, Module, Instance, ClockSignal, ResetSignal


class ISerdes8(Elaboratable):
    def __init__(self, input, ddr_domain, word_domain):
        self.input = input
        self.output = Signal(8)
        self.bitslip = Signal()

        self.ddr_domain = ddr_domain
        self.word_domain = word_domain

    def elaborate(self, platform):
        m = Module()

        m.submodules.iddr = Instance(
            "IDDRX4B",

            i_D=self.input,
            i_ECLK=ClockSignal(self.ddr_domain),
            i_SCLK=ClockSignal(self.word_domain),
            i_RST=ResetSignal(self.word_domain),
            i_ALIGNWD=self.bitslip,

            o_Q0=self.output[0],
            o_Q1=self.output[1],
            o_Q2=self.output[2],
            o_Q3=self.output[3],
            o_Q4=self.output[4],
            o_Q5=self.output[5],
            o_Q6=self.output[6],
            o_Q7=self.output[7],
        )

        return m