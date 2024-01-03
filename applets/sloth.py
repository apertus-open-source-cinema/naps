from amaranth import *
from naps import *
from naps.platform.prjsloth_platform import PrjSlothPlatform


class Top(Elaboratable):
    def elaborate(self, platform: PrjSlothPlatform):
        m = Module()


        # Control Pane
        i2c_pads = platform.request("i2c")
        m.submodules.i2c = BitbangI2c(i2c_pads)

        power_control = platform.request("power_ctl")
        
        for name, *_ in power_control.layout:
            cs = ControlSignal(name=name)
            setattr(self, name, cs)
            m.d.comb += power_control[name].o.eq(cs)

        m.submodules.hmcad_spi = HMCAD1511SPI()

        return m
    
class HMCAD1511SPI(Elaboratable):
    """A bitbanged SPI write only controller for the HMCAD1511 ADC
    """

    def __init__(self) -> None:
        self.cs = ControlSignal()
        self.clk = ControlSignal()
        self.copi = ControlSignal()

    def elaborate(self, platform):
        m = Module()

        adc_spi = platform.request("hmcad1511_spi")
        m.d.comb += [
            adc_spi.cs.o.eq(self.cs),
            adc_spi.clk.o.eq(self.clk),
            adc_spi.copi.o.eq(self.copi)
        ]

        return m
    
    @driver_method
    def write_word(self, address: int, data: int):
        self.cs = 0
        self.cs = 1

        for bit in reversed(range(8)):
            self.clk = 0
            self.copi = address >> bit & 0b1
            self.clk = 1
        
        for bit in reversed(range(16)):
            self.clk = 0
            self.copi = data >> bit & 0b1
            self.clk = 1

        self.cs = 0

if __name__ == "__main__":
    cli(Top, runs_on=(PrjSlothPlatform,), possible_socs=(ZynqSocPlatform, ))
