from nmigen import *

from naps.cores.peripherals.mmio_gpio import MmioGpio
from naps.soc.devicetree_overlay import devicetree_overlay
from naps.soc.soc_platform import SocPlatform

__all__ = ["BitbangSPI"]


class BitbangSPI(Elaboratable):
    def __init__(self, pins, name_suffix=""):
        self.devicetree_name = "bitbang_spi" + name_suffix
        self.pins = pins

    def elaborate(self, platform: SocPlatform):
        m = Module()

        # for some reason, despite CS being specified as active high in the
        # device tree, linux and/or the python spidev module treat it as active
        # low. thus we invert CS here to make the pin active high as defined
        ncs = Record.like(self.pins.cs)
        m.d.comb += self.pins.cs.eq(~ncs)

        self.mmio_gpio = MmioGpio(pads=(self.pins.clk, self.pins.copi, self.pins.cipo, ncs), name_suffix="_" + self.devicetree_name)
        m.submodules.mmio_gpio = self.mmio_gpio

        overlay_content = """
            %overlay_name%: spi@0 {
                compatible = "spi-gpio";
                #address-cells = <1>;
                #size-cells = <0>;
                ranges;

                sck-gpios = <&%mmio_gpio% 0 0>;
                mosi-gpios = <&%mmio_gpio% 1 0>;
                miso-gpios = <&%mmio_gpio% 2 0>;
                cs-gpios = <&%mmio_gpio% 3 0>;
                num_chipselects = <1>;
                status = "ok";

                spidev1 {
                    compatible = "spidev";
                    reg = <0>;      
                    #address-cells = <1>;
                    #size-cells = <0>;
                    spi-max-frequency = <30000000>;
                };
            };
        """
        devicetree_overlay(platform, self.devicetree_name, overlay_content, {"mmio_gpio": self.mmio_gpio.devicetree_name})

        return m
