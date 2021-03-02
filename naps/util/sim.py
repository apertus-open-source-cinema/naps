import inspect
from os.path import join, dirname
from pathlib import Path

from nmigen import *
from nmigen import Signal
from nmigen.hdl.ast import UserValue
from nmigen.sim import Simulator

__all__ = ["SimPlatform", "FakeResource", "TristateIo", "wait_for", "pulse", "do_nothing"]


class SimPlatform:
    def __init__(self, filename=None):
        self.command_templates = []

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

    def sim(self, dut, testbench=None, traces=(), engine="pysim"):
        dut = self.prepare(dut)
        self.fragment = dut
        simulator = Simulator(dut, engine=engine)
        for name, frequency in self.clocks.items():
            simulator.add_clock(1 / frequency, domain=name)

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


class TristateIo:
    def __init__(self, shape=None):
        self.i = Signal(shape)
        self.o = Signal(shape)
        self.oe = Signal()


def wait_for(expr, timeout=100, must_clock=True):
    if must_clock:
        yield

    i = 0
    while True:
        if timeout != -1 and i >= timeout:
            raise TimeoutError("{} did not become '1' within {} cycles".format(expr, timeout))
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
