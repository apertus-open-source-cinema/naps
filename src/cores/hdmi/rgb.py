from nmigen import Signal

from util.bundle import Bundle


class Rgb(Bundle):
    r = Signal(8)
    g = Signal(8)
    b = Signal(8)