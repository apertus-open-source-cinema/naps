from .xilinx_blackbox import XilinxBlackbox


class Oserdes(XilinxBlackbox):
    module = "OSERDESE2"


class Iserdes(XilinxBlackbox):
    module = "ISERDESE2"


class Idelay(XilinxBlackbox):
    module = "IDELAYE2"


class IdelayCtl(XilinxBlackbox):
    module = "IDELAYCTRL"
