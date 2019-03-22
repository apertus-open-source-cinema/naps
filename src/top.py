from nmigen import *
from nmigen.cli import main

from util import anarchy


class Top:
    """The top entity of the gateware.

    Only instantiates the right parts and connects them.
    Also takes care of the connections managed by the `anarchy`.
    """
    def __init__(self):
        self.sensor_interface = Record([

        ])

        # i2c also somehow belongs to the image sensor. it is shared globally
        self.i2c = Record([
            ("SDA", 1),
            ("SCL", 1)
        ])

        self.plugin_n = Record([
            ("LVDS", 6),
            ("GPIO", 8),
            ("I2C", [
                ("SDA", 1),
                ("SCL", 1)
            ]),
        ])
        self.plugin_s = Record([
            ("LVDS", 6),
            ("GPIO", 8),
            ("I2C", [
                ("SDA", 1),
                ("SCL", 1)
            ]),
        ])

        self.pmod_n = Signal(8)
        self.pmod_s = Signal(8)
        self.pmod_e = Signal(4)

        self.ws2812 = Signal()
        self.encoder = Record([
            ("push", 1),
            ("greycode", 2)
        ])

        # as the very last step, assign the out of tree resources
        anarchy.add_params(self)

    def elaborate(self, platform):
        m = Module()
        return m


if __name__ == "__main__":
    top = Top()
    ports = [prop for prop in map(lambda name: getattr(top, name), dir(top)) if isinstance(prop, Signal)]
    main(top, ports=ports)
