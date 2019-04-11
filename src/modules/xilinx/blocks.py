from .xilinx_blackbox import XilinxBlackbox


class Ps7(XilinxBlackbox):
    module = "PS7"


class MMCM(XilinxBlackbox):
    module = "MMCME2_BASE"
