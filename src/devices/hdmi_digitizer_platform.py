from nmigen.build import *

__all__ = ["HdmiDigitizerPlatform"]

from nmigen_boards.resources import LEDResources

from devices.te0714_03_50_2l import TE0714_03_50_2LPlatform


class HdmiDigitizerPlatform(TE0714_03_50_2LPlatform):
    def __init__(self):
        super().__init__()
        self.add_resources([
            *LEDResources(pins="59 61 63 65 85 87 89 91", conn=("JM2", 0), invert=True, attrs=Attrs(IOSTANDARD="LVCMOS18")),

            Resource("ft601", 0,
                Subsignal("reset", PinsN("39", dir="o", conn=("JM2", 0))),
                Subsignal("data", Pins("34 32 30 28 26 24 22 20 16 14 12 10 8 6 4 2"
                                       " 1 3 5 7 9 11 13 15 19 21 23 25 27 29 31 33",
                                       dir="io", conn=("JM2", 0))),
                Subsignal("be", Pins("45 51 44 48", dir="io", conn=("JM2", 0))),
                Subsignal("oe", PinsN("41", dir="o", conn=("JM2", 0))),
                Subsignal("read", PinsN("43", dir="o", conn=("JM2", 0))),
                Subsignal("write", PinsN("47", dir="o", conn=("JM2", 0))),
                Subsignal("siwu", PinsN("46", dir="o", conn=("JM2", 0))),
                Subsignal("rxf", PinsN("42", dir="i", conn=("JM2", 0))),
                Subsignal("txe", PinsN("49", dir="i", conn=("JM2", 0))),
                Subsignal("wakeup", PinsN("37", dir="io", conn=("JM2", 0))),
                Subsignal("clk", Pins("40", dir="i", conn=("JM2", 0))),

                Attrs(IOSTANDARD="LVCMOS33"),
            ),
        ])
