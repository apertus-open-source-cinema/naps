from nmigen import *

from modules.axi.axi import AxiInterface
from modules.axi.axil_reg import AxiLiteReg


class AxilCsrBank(Elaboratable):
    def __init__(self, axil_master: AxiInterface, base_address=0x4000_0000):
        self.axil_master = axil_master
        self.next_address = base_address
        self.slave_num = 0
        self.memory_map = {}

        self.frozen = False
        self.m = Module()

    def reg(self, name, width=32, writable=True):
        assert not self.frozen
        assert name not in self.memory_map

        axil_reg = AxiLiteReg(width=width, base_address=self.next_address, writable=writable, name=name)
        setattr(self.m.submodules, "axi_reg#{}".format(self.slave_num), axil_reg)
        self.axil_master.connect_slave(axil_reg.bus)
        self.memory_map[name] = self.next_address

        self.slave_num += 1
        self.next_address += 4
        return axil_reg.reg

    def elaborate(self, platform):
        self.frozen = True

        # write the memory map
        platform.add_file(
            "mmap/regs.csv",
            "\n".join("{},\t0x{:06x}".format(k, v) for k, v in self.memory_map.items())
        )
        platform.add_file(
            "mmap/regs.sh",
            "\n".join("export r_{}=0x{:06x}".format(k, v) for k, v in self.memory_map.items()) + "\n\n" +
            "\n".join("echo {}: $(devmem2 0x{:06x} | sed -r 's|.*: (.*)|\\1|' | tail -n1)".format(k, v) for k, v in
                      self.memory_map.items())
        )

        return self.m
