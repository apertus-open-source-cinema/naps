from nmigen import *

from cores.csr_bank import ControlSignal
from util.instance_helper import InstanceParent


class Oserdes(InstanceParent):
    module = "OSERDESE2"
    source = "+/xilinx/cells_xtra.v"


class Iserdes(InstanceParent):
    module = "ISERDESE2"
    source = "+/xilinx/cells_xtra.v"


class Idelay(InstanceParent):
    module = "IDELAYE2"
    source = "+/xilinx/cells_xtra.v"


class IdelayCtl(InstanceParent):
    module = "IDELAYCTRL"
    source = "+/xilinx/cells_xtra.v"


class OSerdes10(Elaboratable):
    def __init__(self, input: Signal, domain: str, domain_5x: str):
        self.output = Signal()
        self.input = input

        self.domain = domain
        self.domain_5x = domain_5x
        self.invert = ControlSignal()

    def elaborate(self, platform):
        m = Module()

        data = Signal.like(self.input)
        m.d[self.domain] += data.eq(self.input ^ Repl(self.invert, len(self.input)))

        ce = Signal()
        m.d.comb += ce.eq(~ResetSignal(self.domain))

        shift = Signal(2)

        m.submodules += Instance("OSERDESE2",
                                 p_DATA_WIDTH=10, p_TRISTATE_WIDTH=1,
                                 p_DATA_RATE_OQ="DDR", p_DATA_RATE_TQ="DDR",
                                 p_SERDES_MODE="MASTER",

                                 o_OQ=self.output,
                                 i_OCE=ce,
                                 i_TCE=0,
                                 i_RST=ResetSignal(self.domain),
                                 i_CLK=ClockSignal(self.domain_5x), i_CLKDIV=ClockSignal(self.domain),
                                 i_D1=data[0], i_D2=data[1],
                                 i_D3=data[2], i_D4=data[3],
                                 i_D5=data[4], i_D6=data[5],
                                 i_D7=data[6], i_D8=data[7],

                                 i_SHIFTIN1=shift[0], i_SHIFTIN2=shift[1],
                                 )

        m.submodules += Instance("OSERDESE2",
                                 p_DATA_WIDTH=10, p_TRISTATE_WIDTH=1,
                                 p_DATA_RATE_OQ="DDR", p_DATA_RATE_TQ="DDR",
                                 p_SERDES_MODE="SLAVE",

                                 i_OCE=ce,
                                 i_TCE=0,
                                 i_RST=ResetSignal(self.domain),
                                 i_CLK=ClockSignal(self.domain_5x), i_CLKDIV=ClockSignal(self.domain),
                                 i_D1=0, i_D2=0,
                                 i_D3=data[8], i_D4=data[9],
                                 i_D5=0, i_D6=0,
                                 i_D7=0, i_D8=0,

                                 i_SHIFTIN1=0, i_SHIFTIN2=0,
                                 o_SHIFTOUT1=shift[0], o_SHIFTOUT2=shift[1]
                                 )

        return m
