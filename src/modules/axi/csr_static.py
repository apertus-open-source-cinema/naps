import re
from enum import Enum, auto

from nmigen import Signal, Elaboratable, Module
from nmigen.hdl.ast import UserValue

from modules.axi.axi import AxiInterface, Response
from modules.axi.lite_slave import AxiLiteSlave
from util.nmigen import get_signals, iterator_with_if_elif


class Direction(Enum):
    R = auto()
    RW = auto()


def parse_address_string(string):
    return [int(s, 0) if s else None for s in
            re.match("(0x[0-9a-fA-F]+):?(\\d+)?-?(\\d+)?", string).groups()]


class Reg(Signal):
    def __init__(self, address, rw, *args, **kwargs):
        self.base_addr, self.start_bit, self.stop_bit = parse_address_string(address)
        width = self.start_bit - self.stop_bit + 1 if self.start_bit and self.stop_bit \
            else (1 if self.start_bit else 32)
        self.rw = rw

        super().__init__(width, *args, **kwargs)


class EventReg(UserValue):
    def __init__(self, address):
        super().__init__()
        self.base_addr, self.start_bit, self.stop_bit = parse_address_string(address)

        # we do nothing as a default
        self.on_read = lambda: 0
        self.on_write = lambda written: None

    # this is just to indicate, that we are a first class nmigen type that is found during nmigen-ish things discovery
    # and to silence the warning, that we are not implementing all necessary methods to be a UserValue
    def lower(self):
        raise NotImplementedError


class StaticCsrBank(Elaboratable):
    def __init__(self, axil_master, base_address, thing_with_registers):
        self._axil_master: AxiInterface = axil_master
        self._thing_with_registers = thing_with_registers
        self._base_address = base_address

    def elaborate(self, platform):
        m = Module()

        regs = [reg for reg in get_signals(self._thing_with_registers) if isinstance(reg, (Reg, EventReg))]
        addrs = list(set(reg.base_addr for reg in regs))

        def handle_read(m, addr, data, resp, read_done):
            for conditional, reg_addr in iterator_with_if_elif(addrs, m):
                with conditional(reg_addr == addr):
                    addressed_regs = [reg for reg in regs if reg.base_addr == reg_addr]
                    for reg in addressed_regs:
                        if isinstance(reg, Reg):
                            m.d.sync += data[reg.stop_bit:reg.start_bit].eq(reg)
                        elif isinstance(reg, EventReg):
                            m.d.sync += data[reg.stop_bit:reg.start_bit].eq(reg.on_read())
            # we always respond with ok to allow for unused addresses
            m.d.sync += resp.eq(Response.OKAY)
            read_done()

        def handle_write(m, addr, data, resp, read_done):
            for conditional, reg_addr in iterator_with_if_elif(addrs, m):
                with conditional(reg_addr == addr):
                    addressed_regs = [reg for reg in regs if reg.base_addr == reg_addr and reg.rw == Direction.RW]
                    for reg in addressed_regs:
                        if isinstance(reg, Reg):
                            m.d.sync += reg.eq(data[reg.stop_bit:reg.start_bit])
                        elif isinstance(reg, EventReg):
                            reg.on_write(data[reg.stop_bit:reg.start_bit])
            # we always respond with ok to allow for unused addresses
            m.d.sync += resp.eq(Response.OKAY)
            read_done()

        axi_slave = m.submodules.axi_slave = AxiLiteSlave(
            address_range=range(self._base_address, self._base_address + max(addrs) + self._axil_master.data_bytes),
            handle_read=handle_read,
            handle_write=handle_write,
            bundle_name="axi_csr_slave"
        )
        m.d.comb += self._axil_master.connect_slave(axi_slave.axi)

        return m
