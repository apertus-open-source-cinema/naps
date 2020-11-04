from nmigen import *

from cores.mmio_gpio import MmioGpio
from soc.devicetree.overlay import devicetree_overlay
from soc.soc_platform import SocPlatform


class BitbangI2c(Elaboratable):
    def __init__(self, pins, name_suffix=""):
        self.devicetree_name = "bitbang_i2c" + name_suffix
        self.mmio_gpio = MmioGpio(pads=(pins.scl, pins.sda), name_suffix="_" + self.devicetree_name)

    def elaborate(self, platform: SocPlatform):
        m = Module()
        m.submodules.mmio_gpio = self.mmio_gpio

        overlay_content = """
            %overlay_name%: i2c@0 {
                compatible = "i2c-gpio";
                sda-gpios = <&%mmio_gpio% 1 6>;
                scl-gpios = <&%mmio_gpio% 0 6>;
                i2c-gpio,delay-us = <2>;        /* ~100 kHz */
                #address-cells = <1>;
                #size-cells = <0>;
            };
        """
        devicetree_overlay(platform, self.devicetree_name, overlay_content, {"mmio_gpio": self.mmio_gpio.devicetree_name})

        return m
