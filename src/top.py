from nmigen import *
from nmigen.cli import main

from util import anarchy
from util.util import flatten_records
from modules.ws2812 import Ws2812
import common.layouts as layouts

class Top:
    """The top entity of the gateware.

    Only instantiates the right parts and connects them.
    Also takes care of the connections managed by the `anarchy`.
    """

    def __init__(self):
        self.sensor = Record(layouts.ar0330)
        self.i2c = Record(layouts.i2c)  # i2c also somehow belongs to the image sensor. it is shared globally

        self.plugin_n = Record(layouts.plugin_module)
        self.plugin_s = Record(layouts.plugin_module)

        self.pmod_n = Signal(8)
        self.pmod_s = Signal(8)
        self.pmod_e = Signal(4)

        self.ws2812 = Signal()
        self.encoder = Record(layouts.encoder)

        # as the very last step, assign the out of tree resources
        anarchy.add_params(self)

    def elaborate(self, platform):
        m = Module()

        ws2812 = Ws2812(self.ws2812, led_number=3)
        m.submodules += ws2812
        for led in ws2812.parallel_in:
            for color in led:
                color = 255

        return m

    def get_ports(self):
        signals_records = [prop for prop in map(lambda name: getattr(self, name), dir(self)) if
                isinstance(prop, Signal) or isinstance(prop, Record)]
        return flatten_records(signals_records)


if __name__ == "__main__":
    top = Top()
    main(top, ports=top.get_ports())
