import re
from enum import Enum, auto

from nmigen import Signal, Elaboratable, Module
from nmigen.hdl.ast import UserValue

from util.nmigen import get_signals


class Direction(Enum):
    W = auto()
    RW = auto()


class Reg(Signal):
    def __init__(self, address, rw, *args, **kwargs):
        self.base_addr, self.start_bit, self.stop_bit = re.match("0x([0-9a-fA-F]+)(:\\d+)?(-\\d+)?", address).groups()
        width = self.stop_bit - self.start_bit if self.start_bit and self.stop_bit \
            else (1 if self.start_bit else 32)
        self.rw = rw

        super().__init__(width, *args, **kwargs)


class EventReg(UserValue):
    def __init__(self, address):
        super().__init__()
        self.base_addr, self.start_bit, self.stop_bit = re.match("0x([0-9a-fA-F]+)(:\\d+)?(-\\d+)?", address).groups()

        self.on_read = lambda: 0
        self.on_write = lambda: None

    # this is jst to indicate, that we are a first class nmigen type that is found during nmigen-ish things discovery
    def lower(self):
        raise NotImplementedError


class RegisterHelper(Elaboratable):
    def __init__(self, thing_with_registers, base_address):
        self.thing_with_registers = thing_with_registers
        self.base_address = base_address

    def elaborate(self, platform):
        m = Module()

        regs = [reg for reg in get_signals(self.thing_with_registers) if isinstance(reg, (Reg, EventReg))]



        return m