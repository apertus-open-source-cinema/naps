from nmigen import *
from nmigen.lib.fifo import SyncFIFO
from naps import nAny


class Ila(Elaboratable):
    def __init__(self, trace_length=1000, fifo_underpower=0.5):
        self.probes = []
        self.triggers = []
        self.trace_length = trace_length
        self.fifo_underpower = fifo_underpower

        self.dropped = Signal(range(trace_length))

    def probe(self, signal):
        self.probes += [signal]
        return signal

    def trigger(self, signal):
        self.triggers += [signal]
        return signal

    def elaborate(self, platform):
        m = Module()

        fifo = m.submodules.fifo_type = SyncFIFO(width=sum(len(probe) for probe in self.probes), depth=int(self.trace_length * self.fifo_underpower), fwft=False)

        current_sample = Signal.like(self.dropped)
        with m.FSM():
            with m.State("IDLE"):
                with m.If(nAny(self.triggers)):
                    m.d.sync += current_sample.eq(0)
                    m.d.sync += self.dropped.eq(0)
                    m.next = "TRIGGERED"
            with m.State("TRIGGERED"):
                m.d.comb += fifo.w_data.eq(Cat(*self.probes))
                m.d.comb += fifo.w_en.eq(1)
                
                with m.If(~fifo.w_rdy):
                    m.d.sync += self.dropped.eq(self.dropped + 1)

                with m.If(current_sample < self.trace_length):
                    m.d.sync += current_sample.eq(current_sample + 1)
                with m.Else():
                    m.next = "READOUT"
            with m.State("READOUT"):
                # we stay in this state forever, until we are reset
                # readout happens via axi
                pass

        return m
