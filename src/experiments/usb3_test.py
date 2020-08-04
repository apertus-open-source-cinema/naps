from nmigen import *

from cores.ft601_counter import FT601Counter
from soc.cli import cli


class Top(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, platform):
        m = Module()

        ft601 = platform.request("ft601")
        ft_601_counter = m.submodules.ft601_counter = FT601Counter(ft601)

        for i in range(8):
            m.d.comb += platform.request("led", i).eq(ft_601_counter.counter[-(i + 1)])

        return m


if __name__ == "__main__":
    with cli(Top, soc=False) as platform:
        pass
