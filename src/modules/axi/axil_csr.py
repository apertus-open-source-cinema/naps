from nmigen import *

from modules.axi.axi import AxiInterface, Response
from modules.axi.axil_slave import AxiLiteSlave
from util.nmigen import get_signals, iterator_with_if_elif
from util.nmigen_types import ControlSignal, StatusSignal


class AxilCsrBank(Elaboratable):
    def __init__(self, axil_master: AxiInterface, base_address=0x4000_0000):
        self._base_address = base_address
        self._axil_master = axil_master
        self._next_address = base_address
        self._memory_map = {}
        self._axi_regs = {}

        self.m = Module()

    def reg(self, name, width=32, writable=True, reset=0):
        assert width <= 32
        assert name not in self._memory_map

        reg = Signal(width, reset=reset, name=name)
        self._axi_regs[name] = (reg, self._next_address - self._base_address, writable)
        self._memory_map[name] = self._next_address
        self._next_address += 4

        return reg

    def csr_for_module(self, module, name):
        signals = get_signals(module)
        for signal in signals:
            if isinstance(signal, ControlSignal):
                self.m.d.comb += signal.eq(self.reg("{}__{}".format(name, signal.name), width=len(signal), writable=True, reset=signal.reset))
            if isinstance(signal, StatusSignal):
                self.m.d.comb += self.reg("{}__{}".format(name, signal.name), width=len(signal), writable=False).eq(signal)

    def elaborate(self, platform):
        m = self.m

        def handle_read(m, addr, data, resp, read_done):
            for conditional, (signal, csr_addr, writable) in iterator_with_if_elif(self._axi_regs.values(), m):
                with conditional(addr == csr_addr):
                    m.d.sync += data.eq(signal)
                    m.d.sync += resp.eq(Response.OKAY)
                    read_done()

        def handle_write(m, addr, data, resp, write_done):
            for conditional, (signal, csr_addr, writable) in iterator_with_if_elif(self._axi_regs.values(), m):
                with conditional(addr == csr_addr):
                    if writable:
                        m.d.sync += signal.eq(data)
                    m.d.sync += resp.eq(Response.OKAY)
                    write_done()

        axi_slave = m.submodules.axi_slave = AxiLiteSlave(
            address_range=range(self._base_address, max(self._memory_map.values()) + 1),
            handle_read=handle_read,
            handle_write=handle_write,
            bundle_name="axi_csr_slave"
        )
        m.d.comb += self._axil_master.connect_slave(axi_slave.axi)

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
