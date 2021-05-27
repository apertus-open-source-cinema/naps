# Workarounds for https://github.com/nmigen/nmigen/issues/372
# (DomainRenamer and Sample do not work together)

from nmigen import *
from .nmigen_misc import delay_by


__all__ = ["Sample", "Rose", "Fell", "Changed", "NewHere"]


def Sample(m, signal: Signal, clocks=1, domain="sync"):
    if clocks == 0:
        return signal
    inner_module = Module()  # we create our own module to be free of all conditional statements
    m.submodules += DomainRenamer(domain)(inner_module)
    return delay_by(signal, clocks, inner_module)


def Rose(m, expr: Signal, domain="sync", clocks=0):
    return ~Sample(m, expr, clocks + 1, domain) & Sample(m, expr, clocks, domain)


def Fell(m, expr: Signal, domain="sync", clocks=0):
    return Sample(m, expr, clocks + 1, domain) & ~Sample(m, expr, clocks, domain)


def Changed(m, expr: Signal, domain="sync", clocks=0):
    return Sample(m, expr, clocks + 1, domain) != Sample(m, expr, clocks, domain)


def NewHere(m):
    _new_here_is_here = Signal()
    m.d.comb += _new_here_is_here.eq(1)
    return Rose(m, _new_here_is_here)
