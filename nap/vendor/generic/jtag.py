from nmigen import *
from ..platform_agnostic_elaboratable import PlatformAgnosticElaboratable

__all__ = ["JTAG"]


class JTAG(PlatformAgnosticElaboratable):
    def __init__(self, jtag_domain="jtag"):
        self.shift = Signal()
        self.tdi = Signal()
        self.tdo = Signal()
        self.jtag_domain = jtag_domain
