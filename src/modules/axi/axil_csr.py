from nmigen import *

from modules.axi.axi import AxiInterface
from modules.axi.axil_reg import AxiLiteReg
from modules.axi.interconnect import AxiInterconnect
from util.nmigen import get_signals


class ControlSignal(Signal):
    """ Just a Signal. Indicator, that it is for controlling some parameter (i.e. can be written from the outside)
    """


class StatusSignal(Signal):
    """ Just a Signal. Indicator, that it is for communicating the state to the outside world (i.e. can be read but not written from the outside)
    """


class AxilCsrBank(Elaboratable):
    def __init__(self, axil_master: AxiInterface, base_address=0x4000_0000):
        self._axil_master = axil_master
        self._next_address = base_address
        self._memorybase_address_map = {}
        self._axi_regs = {}
        self.m = Module()

    def reg(self, name, width=32, writable=True, reset=0):
        assert name not in self._memory_map

        reg = AxiLiteReg(width=width, base_address=self._next_address, writable=writable, name=name, reset=reset)
        self._axi_regs[name] = reg
        self._memory_map[name] = self._next_address
        self._next_address += 4

        return reg.reg

    def csr_for_module(self, module, name):
        signals = get_signals(module)
        for signal in signals:
            if isinstance(signal, ControlSignal):
                self.m.d.comb += signal.eq(self.reg("{}__{}".format(name, signal.name), width=len(signal), writable=True, reset=signal.reset))
            if isinstance(signal, StatusSignal):
                self.m.d.comb += self.reg("{}__{}".format(name, signal.name), width=len(signal), writable=False).eq(signal)

    def elaborate(self, platform):
        m = self.m

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
