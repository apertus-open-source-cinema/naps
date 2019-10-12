from nmigen.build import Resource, Subsignal, Pins, DiffPairs, Connector, Attrs
from ..common.layouts import gen_plugin_connector
from nmigen_boards.zturn_lite_z010 import ZTurnLiteZ010Platform

class MicroR2Platform(ZTurnLiteZ010Platform):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_resources([
            Resource("sensor", 0,
                Subsignal("shutter", Pins("25", dir='o', conn=("expansion", 0))),
                Subsignal("trigger", Pins("27", dir='o', conn=("expansion", 0))),
                Subsignal("reset", Pins("31", dir='o', conn=("expansion", 0))),
                Subsignal("clk", Pins("33", dir='o', conn=("expansion", 0))),
                Subsignal("lvds_clk", DiffPairs("52", "54", dir='i', conn=("expansion", 0))),
                Subsignal("lvds", DiffPairs("41 45 55 65", "43 47 57 67", dir='i', conn=("expansion", 0))),
            ),
            Resource("i2c", 0,
                Subsignal("scl", Pins("35", dir='io', conn=("expansion", 0))),
                Subsignal("sda", Pins("37", dir='io', conn=("expansion", 0))),
            ),
            Resource("ws2812", 0, Pins("56", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS33")),
            Resource("encoder", 0,
                Subsignal("quadrature", Pins("58 68", dir='i', conn=("expansion", 0))),
                Subsignal("push", Pins("66", dir='i', conn=("expansion", 0)))
            ),
        ])

        self.add_connectors([
            Connector("plugin_s", 0,
                      gen_plugin_connector(
                          lvds=["21 23", "3 5", "9 11", "13 15", "4 6", "10 12"],
                          gpio=[71, 73, 63, 61, 64, 62, 75, 77],
                          i2c=[46, 48]),
                      conn=("expansion", 0),
                      ),

            Connector("plugin_n", 0,
                      gen_plugin_connector(
                          lvds=["14 16", "22 24", "26 28", "32 34", "36 38", "42 44"],
                          gpio=[76, 78, 80, 84, 86, 88, 90, 74],
                          i2c=[52, 54]),
                      conn=("expansion", 0),
                      ),
            Connector("pmod_n", 0, "110 106 100 96 - - 108 104 98 94 - -", conn=("expansion", 0), ),
            Connector("pmod_s", 0, "97 95 89 85 - - 99 93 87 83 - -", conn=("expansion", 0), ),
            Connector("pmod_e", 0, "103 105 107 109 - -", conn=("expansion", 0), ),
        ])
