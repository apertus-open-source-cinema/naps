from enum import Enum
from modulefinder import Module
from typing import Callable
from nmigen import Signal


class Response(Enum):
    OK = 0
    ERR = 1


HandleRead = Callable[[Module, Signal, Signal, Callable[[Response], None]], None]
HandleWrite = Callable[[Module, Signal, Signal, Callable[[Response], None]], None]
