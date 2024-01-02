from amaranth.build import *
from amaranth.vendor import XilinxPlatform

__all__ = ["ZyboPlatform"]


class ZyboPlatform(XilinxPlatform):
    device = "xc7z010"
    package = "clg400"
    speed = "1"
    resources = [
        Resource("hdmi", 0,
             # high speed serial lanes
             Subsignal("clock", DiffPairs("H16", "H17", dir='o'), Attrs(IOSTANDARD="TMDS_33")),
             Subsignal("b", DiffPairs("D19", "D20", dir='o'), Attrs(IOSTANDARD="TMDS_33")),
             Subsignal("g", DiffPairs("C20", "B20", dir='o'), Attrs(IOSTANDARD="TMDS_33")),
             Subsignal("r", DiffPairs("B19", "A20", dir='o'), Attrs(IOSTANDARD="TMDS_33")),
             Subsignal("out_en", Pins("F17", dir='o'), Attrs(IOSTANDARD="LVCMOS33")),
        )
    ]
    connectors = []
