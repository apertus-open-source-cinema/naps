import inspect
from os.path import join, dirname
from pathlib import Path

from amaranth import *
from amaranth import Signal
from amaranth.hdl import ValueCastable
from amaranth.sim import Simulator

__all__ = ["SimPlatform", "FakeResource", "OutputIo", "InputIo", "TristateIo", "TristateDdrIo", "SimDdr", "wait_for", "pulse", "do_nothing", "resolve"]


class SimPlatform:
    command_templates = []

    def __init__(self, filename=None):
        self.clocks = {}
        self.is_sim = True
        self.processes = []
        self.handed_out_resources = {}

        functions = []
        test_class = None
        caller_path = ""
        stack = inspect.stack()
        for frame in stack[1:]:
            if "unittest" in frame.filename:
                if not filename:
                    filename = "__".join(reversed(functions))
                    if test_class:
                        filename = f'{test_class}__{filename}'
                break
            functions.append(frame.function)
            try:
                test_class = frame.frame.f_locals['self'].__class__.__name__
            except:
                pass
            caller_path = frame.filename
        assert isinstance(filename, str)

        target_dir = join(dirname(caller_path), ".sim_results")
        Path(target_dir).mkdir(exist_ok=True)
        self.output_filename_base = join(target_dir, filename)

    def add_file(self, name, contents):
        pass

    def request(self, name, number=0, *args, **kwargs):
        string = "{}#{}".format(name, number)
        if string not in self.handed_out_resources:
            self.handed_out_resources[string] = FakeResource(string, self.handed_out_resources)
        return self.handed_out_resources[string]

    def prepare(self, top_fragment, name="top", *args, **kwargs):
        if hasattr(self, '_soc_platform'):
            top_fragment = self._soc_platform.prepare_soc(top_fragment)
        else:
            top_fragment = Fragment.get(top_fragment, platform=self)

        return top_fragment

    def add_process(self, generator, domain=None):
        self.processes.append((generator, domain))

    def add_sim_clock(self, domain_name, frequency, phase=0):
        self.clocks[domain_name] = (frequency, phase)

    def sim(self, dut, testbench=None, traces=(), engine="pysim"):
        dut = self.prepare(dut)
        self.fragment = dut
        simulator = Simulator(dut, engine=engine)
        for name, (frequency, phase) in self.clocks.items():
            import sys
            print(name, self.clocks, file=sys.stderr)
            simulator.add_clock(1 / frequency, domain=name, phase=phase)

        if isinstance(testbench, tuple):
            generator, domain = testbench
            self.add_process(generator, domain)
        elif inspect.isgeneratorfunction(testbench):
            self.add_process(testbench, "sync")
        elif testbench is None:
            pass
        else:
            raise TypeError("unknown type for testbench")

        for generator, domain in self.processes:
            simulator.add_sync_process(generator, domain=domain)

        print("\nwriting vcd to '{}.vcd'".format(self.output_filename_base))
        with simulator.write_vcd("{}.vcd".format(self.output_filename_base), "{}.gtkw".format(self.output_filename_base),
                                 traces=traces):
            simulator.run()


class FakeResource(ValueCastable):
    def __init__(self, name, handed_out_resources):
        super().__init__()
        self.handed_out_resources = handed_out_resources
        self.name = name
        self._signal = Signal(name=self.name)

    def shape(self):
        return self._signal.shape()

    def as_value(self):
        return self._signal

    def __getattr__(self, item):
        string = "{}.{}".format(self.name, item)
        if item in Value.__dict__:
            return getattr(self._signal, item)
        if string not in self.handed_out_resources:
            self.handed_out_resources[string] = FakeResource(string, self.handed_out_resources)
        return self.handed_out_resources[string]

    def __getitem__(self, item):
        if isinstance(item, slice):
            item = "slice"
        string = "{}.{}".format(self.name, item)
        if string not in self.handed_out_resources:
            self.handed_out_resources[string] = FakeResource(string, self.handed_out_resources)
        return self.handed_out_resources[string]


class OutputIo:
    def __init__(self, shape=None):
        self.o = Signal(shape)

class InputIo:
    def __init__(self, shape=None):
        self.i = Signal(shape)

class TristateIo:
    def __init__(self, shape=None):
        self.i = Signal(shape)
        self.o = Signal(shape)
        self.oe = Signal()

class TristateDdrIo:
    def __init__(self, shape=None):
        self.oe = Signal()

        self.i_clk = Signal()
        self.i0 = Signal(shape)
        self.i1 = Signal(shape)

        self.o_clk = Signal()
        self.o0 = Signal(shape)
        self.o1 = Signal(shape)


class SimDdr(Elaboratable):
    def __init__(self, pins: TristateDdrIo, domain):
        self.pins = pins
        self.domain = domain

        self.o = Signal(pins.o0.shape())

    def elaborate(self, platform):
        m = Module()

        toggle = Signal()
        m.d.sync += toggle.eq(~toggle)
        m.d.comb += self.o.eq(Mux(toggle, self.pins.o0, self.pins.o1))

        return DomainRenamer(self.domain)(m)


def wait_for(expr, timeout=100, must_clock=True):
    if must_clock:
        yield

    i = 0
    while True:
        if timeout != -1 and i >= timeout:
            raise TimeoutError("{!r} did not become '1' within {} cycles".format(expr, timeout))
        i += 1

        if (yield expr):
            return
        yield


def pulse(signal, length=1, after=0):
    yield signal.eq(1)
    for _ in range(length):
        yield
    yield signal.eq(0)
    for _ in range(after):
        yield


def do_nothing(length=10):
    for i in range(length):
        yield  # we expect that nothing happens here


def resolve(expr):
    """Resolves a nMigen expression that can be constantly evaluated to an integer"""

    sim = Simulator(Module())

    a = []

    def testbench():
        a.append((yield expr))

    sim.add_process(testbench)
    sim.run()
    return a[0]
