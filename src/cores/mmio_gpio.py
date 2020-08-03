from typing import Iterable

from nmigen import *

from cores.csr_bank import ControlSignal, StatusSignal
from soc.devicetree.overlay import devicetree_overlay
from util.nmigen_misc import TristateIo


class MmioGpio(Elaboratable):
    def __init__(self, pads, name_suffix=""):
        """ A simple gpio peripheral, that is compatible with the gpio-mmio.c linux kernel pydriver.
        see https://github.com/torvalds/linux/blob/master/drivers/gpio/gpio-mmio.c
        """
        if isinstance(pads, Record):
            self._pads = pads.fields.values()
        elif isinstance(pads, Iterable):
            self._pads = pads
        else:
            raise ValueError("unsupported type for pads")

        # see https://github.com/torvalds/linux/blob/master/drivers/gpio/gpio-mmio.c#L473
        # we are using a configuration with one output one input and one direction register
        w = len(self._pads)
        self.set = ControlSignal(w)
        self.dat = StatusSignal(w)
        self.dirout = ControlSignal(w)

        self.devicetree_name = "mmio_gpio" + name_suffix

    def elaborate(self, platform):
        m = Module()

        overlay_content = """
            %overlay_name%: gpio-controller@40000000 {
                    compatible = "brcm,bcm6345-gpio";
                    reg-names = "set", "dat", "dirout";
                    reg = <%set% 1>, <%dat% 1>, <%dirout% 1>;
            
                    #gpio-cells = <2>;
                    gpio-controller;
            };
        """
        devicetree_overlay(platform, self.devicetree_name, overlay_content, {"set": self.set, "dat": self.dat, "dirout": self.dirout})

        for i, pad in enumerate(self._pads):
            pad: TristateIo
            m.d.comb += self.dat[i].eq(pad.i)
            m.d.comb += pad.oe.eq(self.dirout[i])
            m.d.comb += pad.o.eq(self.set[i])

        return m
