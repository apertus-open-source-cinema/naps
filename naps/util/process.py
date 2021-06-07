# utilities for describing sequential processes in nMigen
from contextlib import contextmanager

from nmigen.utils import bits_for
from nmigen import *

from .past import NewHere

__all__ = ["Process", "process_block", "process_delay", "process_write_to_stream"]


class Process:
    """
    Processes are a utility to ease the writing of sequential steps in a FSM that are seperated by "locks". Each lock takes at least
    one cycle to complete and may be time or event driven. The code between the locks is run in parallel.
    """
    def __init__(self, m: Module, name, to):
        self.m = m
        self.name = name
        self.to = to
        self.stage = 0
        self.last_stage = Const(0, 0)
        self.current_conditional = m.State(name)

    def __enter__(self):
        self.current_conditional.__enter__()
        return self

    def __iadd__(self, other):
        m = self.m

        self.stage += 1
        with other:
            m.next = f"{self.name}_{self.stage}"
            if self.to is not None:
                with m.If(self.stage == self.last_stage):
                    m.next = self.to

        self.current_conditional.__exit__(None, None, None)
        self.current_conditional = m.State(f"{self.name}_{self.stage}")
        self.current_conditional.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.current_conditional.__exit__(exc_type, exc_val, exc_tb)

        self.last_stage.width = bits_for(self.stage)
        self.last_stage.value = self.stage


def process_block(function):
    """
    A decorator that helps writing blocks that are parts of processes.
    See `delay()` for a minimal example of how to use this
    """

    @contextmanager
    def inner(*args, **kwargs):
        stmt = function(*args, **kwargs)
        try:
            if stmt is not None:
                stmt.__enter__()
            yield None
        finally:
            if stmt is not None:
                stmt.__exit__(None, None, None)

    return inner


@process_block
def process_delay(m, cycles):
    if isinstance(cycles, int) and cycles == 1:
        return m.If(True)
    else:
        if isinstance(cycles, Value):
            timer = Signal.like(cycles, name="_delay_timer")
        else:
            timer = Signal(range(cycles - 1), name="_delay_timer")
        with m.If(timer < (cycles - 2)):
            m.d.sync += timer.eq(timer + 1)

        with m.If(NewHere(m)):
            m.d.sync += timer.eq(0)
        return m.Elif(timer >= cycles - 2)


@process_block
def process_write_to_stream(m, stream, **kwargs):
    for key in kwargs:
        m.d.comb += getattr(stream, key).eq(kwargs[key])
    m.d.comb += stream.valid.eq(1)
    return m.If(stream.ready)
