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

    def reg(self, name, width=32, writable=True, reset=0):
        assert not self._frozen
        assert name not in self._memory_map

        reg = AxiLiteReg(width=width, base_address=self._next_address, writable=writable, name=name, reset=reset)
        self._axi_regs[name] = reg
        self._memory_map[name] = self._next_address

        self._next_address += 4
        return reg.reg

    def csr_for_module(self, module, name, inputs=None, outputs=None, **kwargs):
        if outputs is None:
            outputs = []
        if inputs is None:
            inputs = []

        stmts = []
        for input_name in inputs:
            input = getattr(module, input_name)
            if input_name in kwargs:
                reset = kwargs[input_name]
            else:
                reset=0
            stmts += [input.eq(self.reg("{}__{}".format(name, input_name), width=len(input), writable=True, reset=reset))]
        for output_name in outputs:
            output = getattr(module, output_name)
            stmts += [self.reg("{}__{}".format(name, output_name), width=len(output), writable=False).eq(output)]

        return stmts

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
