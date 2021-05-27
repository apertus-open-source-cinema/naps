# utilities for describing sequential processes in nMigen
from contextlib import contextmanager
from nmigen import *

from .past import NewHere

__all__ = ["Process", "process_block", "process_delay", "process_write_to_stream"]


class Process:
    # TODO: think about:
    #       * have a minimum of one cycle delay? (better generated logic)

    # TODO:
    #  * TEST Througly
    #  * Avoid signal vcd pollution
    #  * document behaviour
    def __init__(self, m: Module):
        self.m = m

        self.current_cond_signal = Signal(reset=1, name="_process_initial_cond_signal")
        self.current_cond_signal_gets_zeroed = Signal(reset=1, name="_process_initial_cond_signal_gets_zeroed")
        self.current_conditional = m.If(1)
        self.reset_process = Signal(name="_process_reset")


    def __enter__(self):
        m = self.m
        m.d.comb += self.reset_process.eq(NewHere(m))

        self.current_conditional.__enter__()
        return self

    def __iadd__(self, other):
        self.current_conditional.__exit__(None, None, None)
        m = self.m

        this_stage_is_cleared = Signal(name="_process_stage_is_cleared")
        this_stage_was_cleared = Signal(name="_process_stage_was_cleared")
        with m.If(self.current_cond_signal):
            with other:
                m.d.sync += this_stage_was_cleared.eq(1)
                m.d.comb += this_stage_is_cleared.eq(1)
        with m.If(self.reset_process):
            m.d.sync += this_stage_was_cleared.eq(0)

        with m.If(this_stage_is_cleared | (this_stage_was_cleared & ~self.reset_process)):
            m.d.comb += self.current_cond_signal_gets_zeroed.eq(0)

        self.current_cond_signal = Signal(name="_process_cond_signal")
        m.d.comb += self.current_cond_signal.eq(this_stage_is_cleared | (this_stage_was_cleared & ~self.reset_process))

        self.current_cond_signal_gets_zeroed = Signal(name="_process_cond_signal_gets_zeroed")
        m.d.comb += self.current_cond_signal_gets_zeroed.eq(self.current_cond_signal)
        self.current_conditional = m.If(self.current_cond_signal_gets_zeroed)
        self.current_conditional.__enter__()
        return self

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

    timer = Signal(range(cycles), name="_delay_timer")
    with m.If(timer < (cycles - 1)):
        m.d.sync += timer.eq(timer + 1)

    with m.If(NewHere(m)):
        m.d.sync += timer.eq(0)
    return m.Elif(timer >= cycles - 1)


@process_block
def process_write_to_stream(m, stream, data):
    m.d.comb += stream.payload.eq(data)
    m.d.comb += stream.valid.eq(1)
    return m.If(stream.ready)
