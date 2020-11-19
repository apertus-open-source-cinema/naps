from nmigen import *

from lib.primitives.platform_agnostic_elaboratable import PlatformAgnosticElaboratable


class JTAG(PlatformAgnosticElaboratable):
    def __init__(self, jtag_domain="jtag"):
        self.shift_tdi = Signal()
        self.shift_tdo = Signal()
        self.tdi = Signal()
        self.tdo = Signal()
        self.jtag_domain = jtag_domain
