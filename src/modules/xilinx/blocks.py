from .xilinx_blackbox import XilinxBlackbox
from ..axi import axi
from ..axi.axi import AxiInterface


class Ps7(XilinxBlackbox):
    module = "PS7"


class Oserdes(XilinxBlackbox):
    module = "OSERDESE2"


class Iserdes(XilinxBlackbox):
    module = "ISERDESE2"


class Idelay(XilinxBlackbox):
    module = "IDELAYE2"


class IdelayCtl(XilinxBlackbox):
    module = "IDELAYCTRL"


class RawPll(XilinxBlackbox):
    module = "PLLE2_BASE"


class Bufg(XilinxBlackbox):
    module = "BUFG"

class Mmcm(XilinxBlackbox):
    module = "MMCME2_ADV"