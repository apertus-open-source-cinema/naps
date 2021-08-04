import sys
from math import ceil
from nmigen import *
from nmigen.hdl.dsl import FSM
from nmigen.lib.cdc import FFSynchronizer

from naps import StatusSignal, ControlSignal, driver_method, Changed, SocPlatform
from ..peripherals import SocMemory

__all__ = ["probe", "fsm_probe", "trigger", "add_ila"]


def fsm_probe(m, fsm: FSM):
    probe(m, fsm.state, decoder=fsm.decoding)


def probe(m, signal, name=None, decoder=None):
    name = name if name else signal.name

    class Probe(Elaboratable):  # we use this to get the platform from the module
        def elaborate(self, platform):
            if not hasattr(platform, "probes"):
                platform.probes = {}
            if name in platform.probes:
                platform.ila_error = KeyError(f"probe with name '{name}' more than once in design")
            platform.probes[name] = (signal, None if decoder is None else dict(decoder))
            return Module()

    m.submodules += Probe()
    return signal


def trigger(m, signal):
    class Trigger(Elaboratable):  # we use this to get the platform from the module
        def elaborate(self, platform):
            if not hasattr(platform, "trigger"):
                platform.trigger = signal
            else:
                platform.ila_error = KeyError("more than one trigger in design")
            return Module()

    m.submodules += Trigger()
    return signal


def add_ila(platform: SocPlatform, *args, domain="sync", **kwargs):
    assert isinstance(platform, SocPlatform)
    sys.setrecursionlimit(500)
    platform.to_inject_subfragments.append((DomainRenamer(domain)(Ila(*args, **kwargs)), 'ila'))


class Ila(Elaboratable):
    def __init__(self, trace_length=2048, after_trigger=None):
        self.trace_length = trace_length

        self.after_trigger = ControlSignal(range(trace_length), reset=(trace_length // 2 if after_trigger is None else after_trigger))
        self.reset = ControlSignal()

        # Yosys cannot handle a signal named `initial` (bug #2914)
        self.initial_ = StatusSignal(reset=1)
        self.running = StatusSignal()
        self.write_ptr = StatusSignal(range(trace_length))
        self.trigger_since = StatusSignal(range(trace_length + 1))
        self.probes = []
        self.decoders = []

    def elaborate(self, platform):
        m = Module()

        if hasattr(platform, "ila_error"):
            raise platform.ila_error

        after_trigger = Signal.like(self.after_trigger)
        m.submodules += FFSynchronizer(self.after_trigger, after_trigger)

        assert hasattr(platform, "trigger"), "No trigger in Design"
        trigger = Signal()
        m.submodules += FFSynchronizer(platform.trigger, trigger)
        assert hasattr(platform, "probes"), "No probes in Design"
        platform_probes = list(platform.probes.items())
        probes = [(k, Signal.like(signal)) for k, (signal, decoder) in platform_probes]
        for (_, (i, _)), (_, o) in zip(platform_probes, probes):
            m.submodules += FFSynchronizer(i, o)
        self.probes = [(k, (len(signal), decoder)) for k, (signal, decoder) in platform_probes]

        probe_bits = sum(length for name, (length, decoder) in self.probes)
        print(f"ila: using {probe_bits} probe bits")
        self.mem = m.submodules.mem = SocMemory(
            width=ceil(probe_bits / 32) * 32, depth=self.trace_length,
            soc_write=False, attrs=dict(syn_ramstyle="block_ram")
        )
        write_port = m.submodules.write_port = self.mem.write_port(domain="sync")

        since_reset = Signal(range(self.trace_length + 1))
        with m.If(self.running):
            with m.If(self.write_ptr < (self.trace_length - 1)):
                m.d.sync += self.write_ptr.eq(self.write_ptr + 1)
            with m.Else():
                m.d.sync += self.write_ptr.eq(0)
            m.d.comb += write_port.addr.eq(self.write_ptr)
            m.d.comb += write_port.en.eq(1)
            m.d.comb += write_port.data.eq(Cat([s for _, s in probes]))

            # we wait trace_length cycles to be sure to overwrite the whole buffer at least once
            # and avoid confusing results
            with m.If(since_reset < self.trace_length):
                m.d.sync += since_reset.eq(since_reset + 1)

            with m.If(self.trigger_since == 0):
                with m.If(trigger & (since_reset > self.trace_length - 1)):
                    m.d.sync += self.trigger_since.eq(1)
            with m.Else():
                with m.If(self.trigger_since < (after_trigger - 1)):
                    m.d.sync += self.trigger_since.eq(self.trigger_since + 1)
                with m.Else():
                    m.d.sync += self.running.eq(0)
                    m.d.sync += self.initial_.eq(0)
        with m.Else():
            reset = Signal()
            m.submodules += FFSynchronizer(self.reset, reset)
            with m.If(Changed(m, reset)):
                m.d.sync += self.running.eq(1)
                m.d.sync += self.trigger_since.eq(0)
                m.d.sync += self.write_ptr.eq(0)
                m.d.sync += since_reset.eq(0)

        return m

    @driver_method
    def arm(self):
        self.reset = not self.reset


    @driver_method
    def get_values(self):
        assert (not self.running) and (not self.initial_), "ila didnt trigger yet"
        r = list(range(self.trace_length))
        addresses = r[self.write_ptr:] + r[:self.write_ptr]
        for address in addresses:
            value = self.mem[address]
            current_offset = 0
            current_row = []
            for name, (size, _) in self.probes:
                current_row.append((value >> current_offset) & (2 ** size - 1))
                current_offset += size
            yield current_row

    @driver_method
    def write_vcd(self, path="/tmp/ila.vcd"):
        from pathlib import Path
        path = Path(path)
        print(f"writing vcd to {path.absolute()}")
        from vcd import VCDWriter
        with open(path, "w") as f:
            with VCDWriter(f) as writer:
                vcd_vars = [(writer.register_var('ila_signals', name, 'reg' if decoder is None else 'string', size=size), decoder) for name, (size, decoder) in self.probes]
                clk = writer.register_var('ila_signals', 'clk', 'reg', size=1)
                for timestamp, values in enumerate(self.get_values()):
                    writer.change(clk, timestamp * 2, 1)
                    for (var, decoder), value in zip(vcd_vars, values):
                        writer.change(var, timestamp * 2, value if decoder is None else decoder.get(value, str(value)))
                    writer.change(clk, timestamp * 2 + 1, 0)
