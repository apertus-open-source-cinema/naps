import sys

from nmigen import *
from naps import StatusSignal, ControlSignal, driver_method, Changed, SocPlatform
from ..peripherals import SocMemory

__all__ = ["probe", "trigger", "add_ila"]


def probe(m, signal, name=None):
    name = name if name else signal.name

    class Probe(Elaboratable):  # we use this to get the platform from the module
        def elaborate(self, platform):
            if not hasattr(platform, "probes"):
                platform.probes = {}
            assert name not in platform.probes
            platform.probes[name] = signal
            return Module()

    m.submodules += Probe()
    return signal


def trigger(m, signal):
    class Trigger(Elaboratable):  # we use this to get the platform from the module
        def elaborate(self, platform):
            if not hasattr(platform, "trigger"):
                platform.trigger = signal
            else:
                raise KeyError("A trigger is already present")
            return Module()

    m.submodules += Trigger()
    return signal


def add_ila(platform: SocPlatform, *args, **kwargs):
    assert isinstance(platform, SocPlatform)
    sys.setrecursionlimit(500)
    platform.to_inject_subfragments.append((Ila(*args, **kwargs), 'ila'))


class Ila(Elaboratable):
    def __init__(self, trace_length=2048, after_trigger=None, clock_freq=100e6):
        self.trace_length = trace_length
        self.clock_freq = clock_freq

        self.after_trigger = ControlSignal(range(trace_length), reset=trace_length // 2 if after_trigger is None else after_trigger)
        self.reset = ControlSignal()

        self.running = StatusSignal()
        self.write_ptr = StatusSignal()
        self.trigger_since = StatusSignal(range(trace_length + 1))
        self.probes = {}

    def elaborate(self, platform):
        m = Module()

        assert hasattr(platform, "trigger"), "No trigger in Design"
        trigger = platform.trigger
        assert hasattr(platform, "probes"), "No probes in Design"
        probes = platform.probes
        self.probes = {k: len(s) for k, s in probes.items()}

        self.mem = m.submodules.mem = SocMemory(width=sum(len(s) for s in probes.keys()), depth=self.trace_length, soc_write=False)
        write_port = m.submodules.write_port = self.mem.write_port(domain="sync")

        with m.If(self.running):
            with m.If(self.write_ptr < self.trace_length):
                m.d.sync += self.write_ptr.eq(self.write_ptr + 1)
            with m.Else():
                m.d.sync += self.write_ptr.eq(0)
            m.d.comb += write_port.addr.eq(self.write_ptr)
            m.d.comb += write_port.en.eq(1)
            m.d.comb += write_port.data.eq(Cat(s for s in probes.values()))

            with m.If(self.trigger_since == 0):
                with m.If(trigger):
                    m.d.sync += self.trigger_since.eq(1)
            with m.Else():
                with m.If(self.trigger_since < self.after_trigger):
                    m.d.sync += self.trigger_since.eq(self.trigger_since + 1)
                with m.Else():
                    m.d.sync += self.running.eq(0)
        with m.Else():
            with m.If(Changed(m, self.reset)):
                m.d.sync += self.running.eq(1)

        return m

    @driver_method
    def arm(self):
        self.reset = not self.reset

    @driver_method
    def write_vcd(self, path="ila.vcd"):
        assert not self.running, "ila didnt trigger yet"
        from pathlib import Path
        path = Path(path)
        print(f"writing vcd to {path.absolute()}")
        r = list(range(self.trace_length))
        addresses = r[self.write_ptr:] + r[:self.write_ptr]
        from vcd import VCDWriter
        with open(path, "w") as f:
            with VCDWriter(f, timescale=(int(1 / self.clock_freq * 1e9), 'ns')) as writer:
                vcd_vars = [writer.register_var('lol', name, 'integer', size=size) for name, size in self.probes.items()]
                for timestamp, address in enumerate(addresses):
                    value = self.mem[address]
                    print(value)
                    current_offset = 0
                    for var in vcd_vars:
                        print(timestamp, (value >> current_offset) & (2 ** var.size - 1))
                        writer.change(var, timestamp, (value >> current_offset) & (2 ** var.size - 1))
                        current_offset += var.size
