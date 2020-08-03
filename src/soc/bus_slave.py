from enum import Enum
from modulefinder import Module
from typing import Callable
from nmigen import Signal

from soc.memorymap import MemoryMap
from util.platform_agnostic_elaboratable import PlatformAgnosticElaboratable


class Response(Enum):
    OK = 0
    ERR = 1


HandleRead = Callable[[Module, Signal, Signal, Callable[[Response], None]], None]
HandleWrite = Callable[[Module, Signal, Signal, Callable[[Response], None]], None]


class BusSlave(PlatformAgnosticElaboratable):
    def __init__(
        self,
        handle_read: HandleRead,
        handle_write: HandleWrite,
        memorymap: MemoryMap
    ):
        """
        Gives an abstract slave for the bus of the Soc.

        read_done / write_done get a Response as an argument

        :param handle_read: a function with the signature handle_read(m, addr, data, read_done) that is used to insert logic to the read path.
        :param handle_write: a function with the signature handle_write(m, addr, data, write_done) that is used to insert logic to the write path.
        :param memorymap: the MemoryMap of the peripheral
        """
        self.handle_read = handle_read
        self.handle_write = handle_write
        self.memorymap = memorymap
