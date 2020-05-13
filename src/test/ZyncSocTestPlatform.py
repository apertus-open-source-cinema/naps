from typing import Callable

from nmigen import *
from nmigen.build import Clock
from nmigen_soc.memory import MemoryMap

from modules.axi.axi import AxiInterface
from modules.axi.lite_slave import AxiLiteSlave
from soc import Response
from soc.SocPlatform import SocPlatform


class AxiSocTestPlatform(SocPlatform):
    def __init__(self, base_addr, sim):
        super().__init__(None)
        self.sim = sim
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
            axi_slave = m.submodules.axi_slave = slave
            m.d.comb += self.axi_lite_master.connect_slave(slave.axi)
            self.inject_subfragment(m)

        self.prepare_hooks.append(axi_wiring_prepare_hook)

    def get_ps7(self):
        pass

    def MemoryMap(self) -> MemoryMap:
        return MemoryMap(addr_width=32, data_width=32, alignment=32)

    def BusSlave(self, handle_read: Callable[[Signal, Signal, Callable[[Response], None]], None],
                 handle_write: Callable[[Signal, Signal, Callable[[Response], None]], None], *, memorymap: MemoryMap):
        axi_lite_slave = AxiLiteSlave(handle_read, handle_write)
        self.axi_lite_slaves.append((axi_lite_slave, memorymap))
