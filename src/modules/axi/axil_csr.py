from nmigen import *

from modules.axi.axi import AxiInterface
from modules.axi.axil_reg import AxiLiteReg
from modules.axi.interconnect import AxiInterconnect


class AxilCsrBank(Elaboratable):
    def __init__(self, axil_master: AxiInterface, base_address=0x4000_0000):
        self._axil_master = axil_master
        self._next_address = base_address
        self._memory_map = {}
        self._axi_regs = {}

        self._frozen = False

    def reg(self, name, width=32, writable=True):
        assert not self._frozen
        assert name not in self._memory_map

        reg = AxiLiteReg(width=width, base_address=self._next_address, writable=writable, name=name)
        self._axi_regs[name] = reg
        self._memory_map[name] = self._next_address

        self._next_address += 4
        return reg.reg

    def elaborate(self, platform):
        self._frozen = True

        m = Module()

        interconnect = m.submodules.interconnect = AxiInterconnect(self._axil_master)

        for name, reg in self._axi_regs.items():
            setattr(m.submodules, "{}_csr".format(name), reg)
            m.d.comb += interconnect.get_port().connect_slave(reg.axi)

        if platform:
            platform.add_file(
                "mmap/regs.csv",
                "\n".join("{},\t0x{:06x}".format(k, v) for k, v in self._memory_map.items())
            )
            platform.add_file(
                "mmap/regs.sh",
                "\n".join("export r_{}=0x{:06x}".format(k, v) for k, v in self._memory_map.items()) + "\n\n" +
                "\n".join("echo {}: $(devmem2 0x{:06x} | sed -r 's|.*: (.*)|\\1|' | tail -n1)".format(k, v) for k, v in
                          self._memory_map.items())
            )

        return m
