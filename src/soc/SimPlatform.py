import inspect

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
        filter_instances(top_fragment)
        return top_fragment

    def sim(self, dut, testbench, filename=None, traces=()):
        dut = self.prepare(dut)
        simulator = Simulator(dut)
        for name, frequency in self.clocks.items():
            simulator.add_clock(1 / frequency, domain=name)

        if not filename:
            filename=inspect.stack()[1][3]

        generator, domain = testbench
        simulator.add_sync_process(generator, domain=domain)
        with simulator.write_vcd(".sim_results/{}.vcd".format(filename), ".sim_results/{}.gtkw".format(filename), traces=traces):
            simulator.run()

    def add_sim_clock(self, domain_name, frequency):
        self.clocks[domain_name] = frequency
