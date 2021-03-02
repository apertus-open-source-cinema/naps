from enum import Enum
from typing import Callable

from nmigen import *

from .memorymap import MemoryMap

__all__ = ["Peripheral", "Response"]


class Response(Enum):
    OK = 0
    ERR = 1


HandleRead = Callable[[Module, Signal, Signal, Callable[[Response], None]], None]
HandleWrite = Callable[[Module, Signal, Signal, Callable[[Response], None]], None]


class Peripheral(Elaboratable):
    def __init__(
            self,
            handle_read: HandleRead,
            handle_write: HandleWrite,
            memorymap: MemoryMap
    ):
        """
        A `Peripheral` is a thing that is memorymaped in the SOC.
        It gets collected and wired up automatically to a platform dependent `Controller` implementation (e.g. an
        `AxiLiteController`) by the concrete SOCPlatform (e.g. the `ZynqSocPlatform`).

        :param handle_read: a function with the signature handle_read(m, addr, data, read_done) that is used to insert
                            logic to the read path. Read_done is a function that gets a Response as an argument
        :param handle_write: a function with the signature handle_write(m, addr, data, write_done) that is used to
                            insert logic to the write path. Write_done is a function that gets a Response as an argument
        :param memorymap: the MemoryMap of the peripheral
        """
        self.handle_read = handle_read
        self.handle_write = handle_write
        self.memorymap = memorymap

    def range(self):
        return self.memorymap.absolute_range_of_direct_children.range()

    def elaborate(self, platform):
        m = Module()
        m.peripheral = self
        return m
