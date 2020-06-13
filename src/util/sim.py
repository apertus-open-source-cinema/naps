import inspect
from pathlib import Path

from nmigen import *
from nmigen.back.pysim import Simulator


class SimPlatform:
    def __init__(self):
        self.clocks = {}
        self.is_sim = True

    def prepare(self, top_fragment, *args, **kwargs):
        # we filter all the instances out, because they give wired behaviour; TODO: this doesnt work :(
        top_fragment: Fragment = Fragment.get(top_fragment, self)

        def filter_instances(top_fragment):
            top_fragment.subfragments = [
                (filter_instances(subfragment), name)
                for subfragment, name in top_fragment.subfragments
                if not isinstance(subfragment, Instance)
            ]
            return top_fragment

        # filter_instances(top_fragment)
        return top_fragment

    def sim(self, dut, testbench, traces=(), filename=None):
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
        else:
            generator = testbench
            domain = "sync"
        simulator.add_sync_process(generator, domain=domain)
        Path(".sim_results/").mkdir(exist_ok=True)
        with simulator.write_vcd(".sim_results/{}.vcd".format(filename), ".sim_results/{}.gtkw".format(filename),
                                 traces=traces):
            simulator.run()

    def add_sim_clock(self, domain_name, frequency):
        self.clocks[domain_name] = frequency

    def add_file(self, filename, contents):
        pass


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
