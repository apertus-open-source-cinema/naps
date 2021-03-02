from nmigen.build import Resource, Pins, DiffPairs, Attrs, Subsignal
from nmigen.vendor.lattice_machxo_2_3l import LatticeMachXO2Platform
from nmigen_boards.microzed_z020 import MicroZedZ020Platform

from .plugins import add_plugin_connector

__all__ = ["BetaPlatform", "BetaRFWPlatform"]


class BetaPlatform(MicroZedZ020Platform):
    def __init__(self):
        super().__init__()
        self.connect_mainboard()

    def connect_mainboard(self):
        add_plugin_connector(
            platform=self, number="south", conn=("JX2", 0),
            lvds=["94 96", "93 95", "97 99", "87 89", "81 83", "73 75"],
        )
        add_plugin_connector(
            platform=self, number="north", conn=("JX1", 0),
            lvds=["68 70", "74 76", "82 84", "92 94", "93 91", "89 87"]
        )

        # TODO: add ext & shield connectors (but how?)
        #       best would be a way to (transpranetly) handle the routing fabrics
        self.add_resources([
            Resource("routing", 'east', DiffPairs('29', '31', dir='io', conn=("JX2", 0)), Attrs(IOSTANDARD="LVCMOS33")),
            Resource("routing", 'west', Pins("56", dir='o', conn=("JX1", 0)), Attrs(IOSTANDARD="LVCMOS33")),
        ])


class BetaRFWPlatform(LatticeMachXO2Platform):
    device = "LCMXO2-2000HC"
    package = "TG100"
    speed = "6"

    resources = [
        Resource(
            "pic_io", 0,
            Subsignal("ss", Pins("27", dir="io"), Attrs(IO_TYPE="LVCMOS33", PULLMODE="UP", DRIVE="4")),
            Subsignal("sck", Pins("31", dir="io"), Attrs(IO_TYPE="LVCMOS33", PULLMODE="UP", DRIVE="4")),
            Subsignal("sdo", Pins("32", dir="io"), Attrs(IO_TYPE="LVCMOS33", PULLMODE="UP", DRIVE="4")),
            Subsignal("pb22b", Pins("47", dir="io"), Attrs(IO_TYPE="LVCMOS33", PULLMODE="UP", DRIVE="4")),
            Subsignal("sn", Pins("48", dir="io"), Attrs(IO_TYPE="LVCMOS33", PULLMODE="UP", DRIVE="4")),
            Subsignal("sdi", Pins("49", dir="io"), Attrs(IO_TYPE="LVCMOS33", PULLMODE="UP", DRIVE="4")),
            Subsignal("done", Pins("76", dir="io"), Attrs(IO_TYPE="LVCMOS33", PULLMODE="UP", DRIVE="4")),
            Subsignal("initn", Pins("77", dir="io"), Attrs(IO_TYPE="LVCMOS33", PULLMODE="UP", DRIVE="4")),
        )
    ]
    connectors = []

    def __init__(self):
        super().__init__()

        add_plugin_connector(self, "north", gpio=["83", "78", "74", "75", "71", "70", "69", "68"])
        add_plugin_connector(self, "south", gpio=["1", "2", "98", "99", "96", "97", "84", "87"])
