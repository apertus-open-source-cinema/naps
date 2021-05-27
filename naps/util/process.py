# utilities for describing sequential processes in nMigen
from contextlib import contextmanager
from nmigen import *

from .past import NewHere

__all__ = ["Process", "process_block", "process_delay", "process_write_to_stream"]


class Process:
    """
    Processes are a list of sequential stages that are seperated by "locks". Each lock takes at least
    one cycle to complete and may be time or event driven. The code between the locks is run in parallel.
    """
    # TODO: think about:
    #       * have a minimum of one cycle delay? (better generated logic)

    # TODO:
    #  * TEST Througly
    #  * Avoid signal vcd pollution
    #  * document behaviour
    def __init__(self, m: Module, name="process"):
        self.m = m
        self.name = name
        self.current_stage = Signal(32, name=f"{name}_stage")  # we just pick a large value here and let the logic optimizer figure the real value out
        self.is_reset = Signal(name=f"{name}_reset")
        self.stage = 0

        self.current_conditional = m.If((self.current_stage == self.stage) | self.is_reset)


    def __enter__(self):
        m = self.m
        with m.If(NewHere(m)):
            self.reset()

        self.current_conditional.__enter__()
        return self

    def __iadd__(self, other):
        m = self.m

        self.stage += 1

        with other:
            m.d.sync += self.current_stage.eq(self.stage)

        self.current_conditional.__exit__(None, None, None)
        self.current_conditional = m.If((self.current_stage == self.stage) & ~self.is_reset)
        self.current_conditional.__enter__()
        return self

    def reset(self):
        with self.m.If(NewHere(self.m)):
            self.m.d.sync += self.current_stage.eq(0)
            self.m.d.comb += self.is_reset.eq(1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.current_conditional.__exit__(exc_type, exc_val, exc_tb)



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
    timer = Signal(range(cycles - 1), name="_delay_timer")
    with m.If(timer < (cycles - 2)):
        m.d.sync += timer.eq(timer + 1)

    with m.If(NewHere(m)):
        m.d.sync += timer.eq(0)
    return m.Elif(timer >= cycles - 2)


@process_block
def process_write_to_stream(m, stream, data):
    m.d.comb += stream.payload.eq(data)
    m.d.comb += stream.valid.eq(1)
    return m.If(stream.ready & stream.valid)
