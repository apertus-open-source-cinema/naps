from nmigen.compat import *
from modules.hdmi.encoder import Encoder

# Serializer and Clocking initial configurations come
# from http://hamsterworks.co.nz/.

class S7HDMIOutEncoderSerializer(Module):
    def __init__(self, bypass_encoder=False, invert=False):
        self.output = Signal()
        if not bypass_encoder:
            self.submodules.encoder = ClockDomainsRenamer("pix")(Encoder())
            self.d, self.c, self.de = self.encoder.d, self.encoder.c, self.encoder.de
            self.data = self.encoder.out
        else:
            self.data = Signal(10)

        # # #

        data = Signal(10)
        if invert:
            self.comb += data.eq(~self.data)
        else:
            self.comb += data.eq(self.data)

        ce = Signal()
        self.sync.pix += ce.eq(~ResetSignal("pix"))

        shift = Signal(2)

        # OSERDESE2 master
        self.specials += [
            Instance("OSERDESE2",
                p_DATA_WIDTH=10, p_TRISTATE_WIDTH=1,
                p_DATA_RATE_OQ="DDR", p_DATA_RATE_TQ="DDR",
                p_SERDES_MODE="MASTER",

                o_OQ=self.output,
                i_OCE=ce,
                i_TCE=Constant(0),
                i_RST=ResetSignal("pix"),
                i_CLK=ClockSignal("pix5x"), i_CLKDIV=ClockSignal("pix"),
                i_D1=data[0], i_D2=data[1],
                i_D3=data[2], i_D4=data[3],
                i_D5=data[4], i_D6=data[5],
                i_D7=data[6], i_D8=data[7],

                i_SHIFTIN1=shift[0], i_SHIFTIN2=shift[1],
                #o_SHIFTOUT1=, o_SHIFTOUT2=,
            ),
            Instance("OSERDESE2",
                p_DATA_WIDTH=10, p_TRISTATE_WIDTH=1,
                p_DATA_RATE_OQ="DDR", p_DATA_RATE_TQ="DDR",
                p_SERDES_MODE="SLAVE",

                i_OCE=ce,
                i_TCE=Constant(0),
                i_RST=ResetSignal("pix"),
                i_CLK=ClockSignal("pix5x"), i_CLKDIV=ClockSignal("pix"),
                i_D1=Constant(0), i_D2=Constant(0),
                i_D3=data[8], i_D4=data[9],
                i_D5=Constant(0), i_D6=Constant(0),
                i_D7=Constant(0), i_D8=Constant(0),

                i_SHIFTIN1=Constant(0), i_SHIFTIN2=Constant(0),
                o_SHIFTOUT1=shift[0], o_SHIFTOUT2=shift[1]
            ),
        ]

class HDMIOutPHY(Module):
    def __init__(self):
        self.hsync = Signal()
        self.vsync = Signal()
        self.data_enable = Signal()
        self.r = Signal(8)
        self.g = Signal(8)
        self.b = Signal(8)
        self.outputs = Signal(3)
        self.clock = Signal()

        # # #

        clk_gen = self.submodules.clk_gen = S7HDMIOutEncoderSerializer(bypass_encoder=True)
        self.comb += self.clk_gen.data.eq(Signal(10, reset=0b1111100000))
        self.comb += self.clock.eq(clk_gen.output)

        es_b = self.submodules.es_b = S7HDMIOutEncoderSerializer()
        es_g = self.submodules.es_g = S7HDMIOutEncoderSerializer()
        es_r = self.submodules.es_r = S7HDMIOutEncoderSerializer(invert=True)  # TODO: more sensible
        self.comb += self.outputs.eq(Cat(es_b.output, es_g.output, es_r.output))

        self.comb += [
            es_b.d.eq(self.b),
            es_g.d.eq(self.g),
            es_r.d.eq(self.r),
            es_b.c.eq(Cat(self.hsync, self.vsync)),
            es_g.c.eq(0),
            es_r.c.eq(0),
            es_b.de.eq(self.data_enable),
            es_g.de.eq(self.data_enable),
            es_r.de.eq(self.data_enable)
        ]
