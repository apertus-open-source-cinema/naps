from nmigen.compat import *
from modules.vendor.litevideo_hdmi.encoder import Encoder

# Serializer and Clocking initial configurations come
# from http://hamsterworks.co.nz/.

class S7HDMIOutEncoderSerializer(Module):
    def __init__(self, bypass_encoder=False):
        self.output = Signal()
        if not bypass_encoder:
            self.submodules.encoder = ClockDomainsRenamer("pix")(Encoder())
            self.d, self.c, self.de = self.encoder.d, self.encoder.c, self.encoder.de
            self.data = self.encoder.out
        else:
            self.data = Signal(10)

        # # #

        data = Signal(10)
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


# This assumes a 100MHz base clock
class S7HDMIOutClocking(Module):
    def __init__(self):
        self.clock_domains.cd_pix = ClockDomain("pix")
        self.clock_domains.cd_pix5x = ClockDomain("pix5x", reset_less=True)

        # # #

        mmcm_locked = Signal()
        mmcm_fb = Signal()
        mmcm_clk0 = Signal()
        mmcm_clk1 = Signal()
        mmcm_drdy = Signal()

        self.specials += [
            Instance("MMCME2_ADV",
                p_BANDWIDTH="OPTIMIZED",
                i_RST=Constant(0), o_LOCKED=mmcm_locked,

                # VCO
                p_REF_JITTER1=0.01, p_CLKIN1_PERIOD=10.0,
                p_CLKFBOUT_MULT_F=30.0, p_CLKFBOUT_PHASE=0.000, p_DIVCLK_DIVIDE=2,
                i_CLKIN1=ClockSignal("sync"), i_CLKFBIN=mmcm_fb, o_CLKFBOUT=mmcm_fb,

                # CLK0
                p_CLKOUT0_DIVIDE_F=10.0, p_CLKOUT0_PHASE=0.000, o_CLKOUT0=mmcm_clk0,
                # CLK1
                p_CLKOUT1_DIVIDE=2, p_CLKOUT1_PHASE=0.000, o_CLKOUT1=mmcm_clk1,

            ),
            Instance("BUFG", i_I=mmcm_clk0, o_O=self.cd_pix.clk),
            Instance("BUFG", i_I=mmcm_clk1, o_O=self.cd_pix5x.clk)
        ]
        self.comb += self.cd_pix.rst.eq(~mmcm_locked)


class S7HDMIOutPHY(Module):
    def __init__(self):
        self.hsync = Signal()
        self.vsync = Signal()
        self.data_enable = Signal()
        self.r = Signal(8)
        self.g = Signal(8)
        self.b = Signal(8)
        self.outputs = Signal(3)

        # # #

        es0 = self.submodules.es0 = S7HDMIOutEncoderSerializer()
        es1 = self.submodules.es1 = S7HDMIOutEncoderSerializer()
        es2 = self.submodules.es2 = S7HDMIOutEncoderSerializer()
        self.comb += self.outputs.eq(Cat(es0.output, es1.output, es2.output))

        self.comb += [
            self.es0.d.eq(self.b),
            self.es1.d.eq(self.g),
            self.es2.d.eq(self.r),
            self.es0.c.eq(Cat(self.hsync, self.vsync)),
            self.es1.c.eq(0),
            self.es2.c.eq(0),
            self.es0.de.eq(self.data_enable),
            self.es1.de.eq(self.data_enable),
            self.es2.de.eq(self.data_enable)
        ]
