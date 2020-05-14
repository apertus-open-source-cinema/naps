import inspect
from typing import Callable

from nmigen import *
from nmigen.back.pysim import Simulator
from nmigen.build import Clock
from nmigen.compat import bits_for
from nmigen_soc.memory import MemoryMap

from modules.axi.axi import AxiInterface
from modules.axi.lite_slave import AxiLiteSlave
from soc import Response, MemoryMapFactory
from soc.SocPlatform import SocPlatform


class ZynqSocTestPlatform(SocPlatform):
    def __init__(self, base_addr):
        super().__init__(None)
        MemoryMapFactory.memorymap_factory_method = lambda: MemoryMap(data_width=32, addr_width=32, alignment=bits_for(4) - 1)
        self.real_prepare = lambda fragment, *args, **kwargs: fragment

        self.base_addr = base_addr
        self.axi_lite_master = AxiInterface(addr_bits=32, data_bits=32, master=True, lite=True)
        self.axi_lite_slaves = []


        def axi_wiring_prepare_hook(top_elaboratable, sames):
            assert len(self.axi_lite_slaves) == 1
            memorymap: MemoryMap
            slave: AxiLiteSlave
            slave, memorymap = self.axi_lite_slaves[0]

            max_addr = max(end for resource, (start, end, width) in memorymap.all_resources())
            slave.address_range = range(self.base_addr, self.base_addr + max_addr)

            m = Module()
            m.submodules.axi_slave = slave
            m.d.comb += self.axi_lite_master.connect_slave(slave.axi)
            self.to_inject_subfragments((m, None))

        self.prepare_hooks.append(axi_wiring_prepare_hook)

    def MemoryMap(self) -> MemoryMap:
        return MemoryMap(addr_width=32, data_width=32, alignment=32)

    def BusSlave(self, handle_read: Callable[[Signal, Signal, Callable[[Response], None]], None],
                 handle_write: Callable[[Signal, Signal, Callable[[Response], None]], None], *, memorymap: MemoryMap):
        axi_lite_slave = AxiLiteSlave(handle_read, handle_write)
        self.axi_lite_slaves.append((axi_lite_slave, memorymap))

    def sim(self, dut, testbench, filename=None, traces=None, simulator=None):
        if not filename:
            filename=inspect.stack()[1][3]
        if not simulator:
            dut = self.prepare(dut)
            simulator = Simulator(dut)
        if not traces:
            traces = self.axi_lite_master._rhs_signals()

        simulator.add_clock(1e-6)
        simulator.add_sync_process(testbench)
        with simulator.write_vcd(".sim_results/{}.vcd".format(filename), ".sim_results/{}.gtkw".format(filename), traces=traces):
            simulator.run()
