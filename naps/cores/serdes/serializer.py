from nmigen import *
from nmigen.lib.cdc import FFSynchronizer
from naps import BasicStream
from ...util.nmigen_misc import fake_differential
from ..stream import BufferedAsyncStreamFIFO

__all__ = ["Serializer"]


class Serializer(Elaboratable):
    def __init__(self, pins, width: int, ddr_domain, reset):
        self.pins = pins
        self.reset = reset
        self.input = BasicStream(width)
        self.idle = Signal(width)
        self.is_idle = Signal()
        self.ddr_domain = ddr_domain

    def elaborate(self, platform):
        m = Module()

        ddr_reset = Signal()
        m.submodules += FFSynchronizer(self.reset, ddr_reset, o_domain=self.ddr_domain)

        m.d.comb += self.pins.o_clk.eq(ClockSignal(self.ddr_domain))
        m.d.comb += self.pins.oe.eq(~self.reset)

        hs_fifo = m.submodules.hs_fifo = BufferedAsyncStreamFIFO(self.input, 8, o_domain=self.ddr_domain)
        hs_payload = Signal(8)

        was_valid = Signal()
        m.submodules += FFSynchronizer(~was_valid, self.is_idle)

        with m.FSM(domain=self.ddr_domain):
            for i in range(4):
                with m.State(f"{i}"):
                    if i == 3:
                        with m.If(hs_fifo.output.valid):
                            m.d[self.ddr_domain] += hs_payload.eq(hs_fifo.output.payload)
                            m.d[self.ddr_domain] += self.idle.eq(Repl(hs_fifo.output.payload[7], 8))
                            m.d[self.ddr_domain] += was_valid.eq(1)
                        with m.Else():
                            m.d[self.ddr_domain] += hs_payload.eq(self.idle)
                            m.d[self.ddr_domain] += was_valid.eq(0)
                        m.d.comb += hs_fifo.output.ready.eq(was_valid)
                    m.d.comb += self.pins.o0.eq(fake_differential(hs_payload[i * 2 + 0]))
                    m.d.comb += self.pins.o1.eq(fake_differential(hs_payload[i * 2 + 1]))
                    m.next = f"{(i + 1) % 4}"

        return ResetInserter({self.ddr_domain: ddr_reset, "sync": self.reset})(m)
