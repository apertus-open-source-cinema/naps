import inspect
from pathlib import Path

from nmigen import *
from nmigen import Signal
from nmigen.hdl.ast import UserValue
from nmigen.sim import Simulator

from util.bundle import Bundle


class SimPlatform:
    def __init__(self):
        self.command_templates = []

        self.clocks = {}
        self.is_sim = True
        self.processes = []
        self.handed_out_resources = {}

    def add_file(self, name, contents):
        pass

    def request(self, name, number=0):
        string = "{}#{}".format(name, number)
        if string not in self.handed_out_resources:
            self.handed_out_resources[string] = FakeResource(string, self.handed_out_resources)
        return self.handed_out_resources[string]

    def prepare(self, top_fragment, name="top", *args, **kwargs):
        # we filter all the instances out, because they give wired behaviour; TODO: this doesnt work :(
        top_fragment: Fragment = Fragment.get(top_fragment, self)

        def filter_instances(top_fragment):
            top_fragment.subfragments = [
                (filter_instances(subfragment), name)
                for subfragment, name in top_fragment.subfragments
                if not (isinstance(subfragment, Instance) and not subfragment.type.startswith('$'))
            ]
            return top_fragment

        filter_instances(top_fragment)
        return top_fragment

    def add_process(self, generator, domain=None):
        self.processes.append((generator, domain))

    def add_sim_clock(self, domain_name, frequency):
        self.clocks[domain_name] = frequency

    def sim(self, dut, testbench=None, traces=(), filename=None):
        dut = self.prepare(dut)
        simulator = Simulator(dut)
        for name, frequency in self.clocks.items():
            simulator.add_clock(1 / frequency, domain=name)

        if not filename:
            stack = inspect.stack()
            filename = stack[1].function
        assert isinstance(filename, str)

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

        Path(".sim_results/").mkdir(exist_ok=True)
        with simulator.write_vcd(".sim_results/{}.vcd".format(filename), ".sim_results/{}.gtkw".format(filename),
                                 traces=traces):
            simulator.run()


class FakeResource(UserValue):
    def __init__(self, name, handed_out_resources):
        super().__init__()
        self.handed_out_resources = handed_out_resources
        self.name = name

    def lower(self):
        return Signal(name=self.name)

    def __getattr__(self, item):
        string = "{}.{}".format(self.name, item)
        if string not in self.handed_out_resources:
            self.handed_out_resources[string] = FakeResource(string, self.handed_out_resources)
        return self.handed_out_resources[string]

    def __getitem__(self, item):
        string = "{}.{}".format(self.name, item)
        if string not in self.handed_out_resources:
            self.handed_out_resources[string] = FakeResource(string, self.handed_out_resources)
        return self.handed_out_resources[string]


def wait_for(expr, timeout=100, must_clock=True):
    for i in range(timeout):
        if i > 0 or must_clock:
            yield
        if (yield expr):
            return
    raise TimeoutError("{} did not become '1' within {} cycles".format(expr, timeout))


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


class TristateIo(Bundle):
    def __init__(self, shape=None):
        super().__init__()
        self.i = Signal(shape)
        self.o = Signal(shape)
        self.oe = Signal()