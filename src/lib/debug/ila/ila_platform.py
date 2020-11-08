from nmigen import *
from nmigen_boards.zturn_lite_z010 import ZTurnLiteZ010Platform


class IlaPlatform:
    def __init__(self, platform):
        self.platform = platform

        self.probes = {}

    # we pass through all platform methods, because we pretend to be one
    def __getattr__(self, item):
        return getattr(self.platform, item)

    def probe(self, signal, name):
        self.probes[name] = signal
        return signal


if __name__ == "__main__":
    class Top(Elaboratable):
        def __init__(self):
            pass

        def elaborate(self, platform):
            m = Module()

            counter = platform.probe(Signal(32), name="counter")
            m.d.sync += counter.eq(counter + 1)

            # add some ila core here

            return m


    platform = IlaPlatform(ZTurnLiteZ010Platform)
    platform.build(Top())