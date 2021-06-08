from nmigen.build import Resource, Pins, PinsN, DiffPairs, DiffPairsN, Attrs, Subsignal
from nmigen.vendor.lattice_machxo_2_3l import LatticeMachXO2Platform
from nmigen_boards.microzed_z020 import MicroZedZ020Platform

from .plugins import add_plugin_connector

__all__ = ["BetaPlatform", "BetaRFWPlatform"]

CMV_LVDS_LANES = (
    # positive    negative
    ("JX2_0:74", "JX2_0:76"), # 0
    ("JX2_0:88", "JX2_0:90"),
    ("JX2_0:68", "JX2_0:70"),
    ("JX2_0:67", "JX2_0:69"),
    ("JX2_0:62", "JX2_0:64"),
    ("JX2_0:61", "JX2_0:63"),
    ("JX2_0:54", "JX2_0:56"),
    ("JX2_0:48", "JX2_0:50"),
    ("JX2_0:47", "JX2_0:49"),
    ("JX2_0:42", "JX2_0:44"),
    ("JX2_0:41", "JX2_0:43"),
    ("JX2_0:36", "JX2_0:38"),
    ("JX2_0:35", "JX2_0:37"),
    ("JX2_0:18", "JX2_0:20"),
    ("JX2_0:30", "JX2_0:32"),
    ("JX2_0:24", "JX2_0:26"),
    ("JX1_0:62", "JX1_0:64"),
    ("JX1_0:54", "JX1_0:56"),
    ("JX2_0:53", "JX2_0:55"), # lane 18 inverted to simplify routing
    ("JX1_0:73", "JX1_0:75"),
    ("JX1_0:67", "JX1_0:69"),
    ("JX1_0:61", "JX1_0:63"),
    ("JX1_0:53", "JX1_0:55"),
    ("JX1_0:47", "JX1_0:49"),
    ("JX1_0:41", "JX1_0:43"),
    ("JX1_0:35", "JX1_0:37"),
    ("JX1_0:42", "JX1_0:44"),
    ("JX1_0:36", "JX1_0:38"),
    ("JX1_0:31", "JX1_0:32"),
    ("JX1_0:11", "JX1_0:13"),
    ("JX1_0:29", "JX1_0:30"),
    ("JX1_0:23", "JX1_0:25"), # 31
)

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

        lvds_lanes = []
        for i, lane in enumerate(CMV_LVDS_LANES):
            lvds_lanes.append(Subsignal(f"lvds_{i}",
                DiffPairs(*lane, dir='i', invert=(i == 18)), # lane 18 inverted to simplify routing
                Attrs(IOSTANDARD="LVDS_25", DIFF_TERM="TRUE", IBUF_LOW_PWR="TRUE")))

        self.add_resources([
            Resource("sensor", 0,
                     Subsignal("clk", Pins("19", dir='o', conn=("JX1", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     Subsignal("reset", PinsN("17", dir='o', conn=("JX1", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     Subsignal("frame_req", Pins("9", dir='o', conn=("JX1", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     Subsignal("t_exp1", Pins("10", dir='o', conn=("JX1", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     Subsignal("t_exp2", Pins("100", dir='o', conn=("JX2", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     Subsignal("lvds_clk", DiffPairs("81", "83", dir='o', conn=("JX1", 0)), Attrs(IOSTANDARD="LVDS_25", SLEW="SLOW")),
                     *lvds_lanes,
                     Subsignal("lvds_ctrl", DiffPairs("82", "84", dir='i', conn=("JX2", 0)), Attrs(IOSTANDARD="LVDS_25", DIFF_TERM="TRUE", IBUF_LOW_PWR="TRUE")),
                     Subsignal("lvds_outclk", DiffPairsN("48", "50", dir='i', conn=("JX2", 0)), Attrs(IOSTANDARD="LVDS_25", DIFF_TERM="TRUE", IBUF_LOW_PWR="TRUE")),
                     ),
            Resource("sensor_spi", 0,
                     Subsignal("cs", Pins("24", dir='o', conn=("JX1", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     Subsignal("clk", Pins("26", dir='o', conn=("JX1", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     Subsignal("copi", Pins("29", dir='o', conn=("JX2", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     Subsignal("cipo", Pins("31", dir='i', conn=("JX2", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     ),
        ])

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
