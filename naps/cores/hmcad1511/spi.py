from amaranth import *
from naps import *

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
            self.copi = (address >> bit) & 0b1
            self.clk = 1
        
        for bit in reversed(range(16)):
            self.clk = 0
            self.copi = (data >> bit) & 0b1
            self.clk = 1

        self.cs = 0

    @driver_method
    def set_test_pattern(self, mode="off"):
        if mode == "off":
            self.write_word(0x45, 0b00)
        elif mode == "sync":
            self.write_word(0x45, 0b10)
        elif mode == "deskew":
            self.write_word(0x45, 0b01)
        else:
            raise ValueError(f"{mode} is not a valid testpattern mode")