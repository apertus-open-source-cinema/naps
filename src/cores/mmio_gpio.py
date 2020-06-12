# TODO: finish
# TODO: add tests

from nmigen import *



class MmioGpio(Elaboratable):
    def __init__(self, pads):
        """ A simple gpio peripheral, that is compatible with the gpio-mmio.c linux kernel driver.
        see https://github.com/torvalds/linux/blob/master/drivers/gpio/gpio-mmio.c
        """
        self._pads = pads

        # registers

    def elaborate(self, platform):
        m = Module()

        return m
