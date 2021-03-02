from nmigen import *
from naps import RGB24


class BertlPatternGenerator(Elaboratable):
    def __init__(self, width, height):
        self.x = Signal.like(width)
        self.y = Signal.like(height)
        self.out = RGB24()

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.out.r.eq(self.x[0:8])
        m.d.comb += self.out.g.eq(self.y[0:8])
        m.d.comb += self.out.b.eq(Cat(Signal(3), self.y[8:10], self.x[8:11]))

        return m


class DimmingPatternGenerator(Elaboratable):
    def __init__(self, width, height):
        self.x = Signal(range(width))
        self.y = Signal(range(height))
        self.out = RGB24()

    def elaborate(self, platform):
        m = Module()

        frame_counter = Signal(range(256 * 3 + 1))
        with m.If((self.x == 0) & (self.y == 0) & (frame_counter < 256 * 3)):
            m.d.sync += frame_counter.eq(frame_counter + 1)
        with m.Elif((self.x == 0) & (self.y == 0)):
            m.d.sync += frame_counter.eq(0)

        with m.If(self.x < 256 * 1):
            m.d.comb += self.out.r.eq(self.x)
        with m.Elif(self.x < 256 * 2):
            m.d.comb += self.out.g.eq(self.x)
        with m.Elif(self.x < 256 * 3):
            m.d.comb += self.out.b.eq(self.x)

        return m