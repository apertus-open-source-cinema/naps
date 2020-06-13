# TODO: add tests
from typing import Iterable

from nmigen import *

from cores.csr_bank import ControlSignal, StatusSignal
from util.nmigen import TristateIo


class MmioGpio(Elaboratable):
    def __init__(self, pads):
        """ A simple gpio peripheral, that is compatible with the gpio-mmio.c linux kernel driver.
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

    def elaborate(self, platform):
        m = Module()

        for i, pad in enumerate(self._pads):
            pad: TristateIo
            m.d.comb += self.dat[i].eq(pad.i)
            m.d.comb += pad.oe.eq(self.dirout[i])
            m.d.comb += pad.o.eq(self.set[i])

        return m
