from nmigen.build import Resource, Pins, DiffPairs, Connector, Attrs

from .microzed_platform import MicroZedZ020Platform
from ..common.layouts import gen_plugin_connector


class BetaPlatform(MicroZedZ020Platform):
    def __init__(self):
        super().__init__()
        self.connect_mainboard()

    def connect_mainboard(self):
        self.add_connectors([
            Connector("plugin", 'south',
                      gen_plugin_connector(
                          lvds=["94 96", "95 93", "97 99", "87 89", "81 83", "73 75"]),
                      conn=("expansion", 1),
                      ),

            Connector("plugin", 'north',
                      gen_plugin_connector(
                          lvds=["68 70", "74 76", "82 84", "94 92", "93 91", "89 87"]),
                      conn=("expansion", 0),
                      ),
        ])

        # TODO: add ext & shield connectors (but how?)
        # best would be a way to (transpranetly) handle the routing fabrics
        self.add_resources([
            Resource("routing", 'east', DiffPairs('29', '31', dir='io', conn=("expansion", 1)),
                     Attrs(IOSTANDARD="LVCMOS33")),
            Resource("routing", 'west', Pins("56", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS33")),
        ])
