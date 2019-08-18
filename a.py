from nmigen_boards.zturn_lite import ZTurnLitePlatform
from nmigen import Module, Signal, ClockDomain


p = ZTurnLitePlatform()

m = Module()
a = Signal()
b = Signal()
m.domains += ClockDomain("sync")
m.d.sync += a.eq(b)

p.build(m)
