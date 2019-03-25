from nmigen import *
from nmigen.cli import main

from util import anarchy
from util.util import flatten_records


class Top:
    """The top entity of the gateware.

    Only instantiates the right parts and connects them.
    Also takes care of the connections managed by the `anarchy`.
    """

    def __init__(self):
        self.sensor = Record([
            ("shutter", 1),
            ("trigger", 1),
            ("clk", 1),
            ("reset", 1),
            ("lvds", 4),
            ("lvds_clk", 1),
        ])

        # i2c also somehow belongs to the image sensor. it is shared globally
        self.i2c = Record([
            ("sda", 1),
            ("scl", 1)
        ])

        self.plugin_n = Record([
            ("lvds", 6),
            ("gpio", 8),
            ("i2c", [
                ("sda", 1),
                ("scl", 1)
            ]),
        ])
        self.plugin_s = Record([
            ("lvds", 6),
            ("gpio", 8),
            ("i2c", [
                ("sda", 1),
                ("scl", 1)
            ]),
        ])

        self.pmod_n = Signal(8)
        self.pmod_s = Signal(8)
        self.pmod_e = Signal(4)

        self.ws2812 = Signal()
        self.encoder = Record([
            ("push", 1),
            ("graycode", 2)
        ])

        # as the very last step, assign the out of tree resources
        anarchy.add_params(self)

    def elaborate(self, platform):
        m = Module()
        return m

    def get_ports(self):
        signals_records = [prop for prop in map(lambda name: getattr(self, name), dir(self)) if
                isinstance(prop, Signal) or isinstance(prop, Record)]
        return flatten_records(signals_records)


if __name__ == "__main__":
    top = Top()
    main(top, ports=top.get_ports())
