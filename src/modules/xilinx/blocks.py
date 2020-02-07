from abc import ABC

from .xilinx_blackbox import XilinxBlackbox


class Ps7(XilinxBlackbox):
    module = "PS7"
