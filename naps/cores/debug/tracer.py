from nmigen import *
from nmigen.hdl.dsl import FSM

from naps import driver_method, StatusSignal, Changed
from ..peripherals import SocMemory

__all__ = ["Tracer"]


class Tracer(Elaboratable):
    def __init__(self, fsm: FSM, trace_length=128):
        self.fsm = fsm
        self.trace_length = trace_length
        self.write_ptr = StatusSignal(range(trace_length))
        self.trace_decoder = {}

    def elaborate(self, platform):
        m = Module()

        mem = m.submodules.mem = SocMemory(width=len(self.fsm.state), depth=self.trace_length, soc_write=False)
        write_port = m.submodules.write_port = mem.write_port(domain="sync")
        with m.If(Changed(m, self.fsm.state)):
            m.d.comb += write_port.en.eq(1)
            m.d.comb += write_port.data.eq(self.fsm.state)
            m.d.comb += write_port.addr.eq(self.write_ptr)
            with m.If(self.write_ptr < self.trace_length):
                m.d.sync += self.write_ptr.eq(self.write_ptr + 1)
            with m.Else():
                m.d.sync += self.write_ptr.eq(0)

        self.trace_decoder.update(self.fsm.decoding)

        return m

    @driver_method
    def print_trace(self):
        r = list(range(self.trace_length))
        for i in r[self.write_ptr:] + r[:self.write_ptr]:
            print(self.trace_decoder[self.mem[i]])
