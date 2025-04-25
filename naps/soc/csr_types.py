from typing import Any
from amaranth import *
from amaranth._unused import MustUse
from amaranth.hdl import ValueCastable

from naps.soc.memorymap import Address
from naps.soc.peripheral import Response

__all__ = ["ControlSignal", "StatusSignal", "EventReg", "PulseReg"]


class UncollectedCsrWarning(Warning):
    pass


class _Csr(MustUse):
    """a marker class to collect the registers easily"""
    _MustUse__warning = UncollectedCsrWarning
    _MustUse__silence = True
    _address = None


class ControlSignal(ValueCastable, _Csr):
    """ Just a Signal. Indicator, that it is for controlling some parameter (i.e. can be written from the outside)
    Is mapped as a CSR in case the design is build with a SocPlatform.
    """

    def __init__(self, shape=None, *, address=None, read_strobe=None, write_strobe=None, src_loc_at=0, **kwargs):
        super.__init__(super())
        self._signal = Signal(shape, src_loc_at=src_loc_at+1, **kwargs, )

        self._address = Address.parse(address)
        self._write_strobe = write_strobe
        self._read_strobe = read_strobe

    def as_value(self):
        return self._signal

    def shape(self):
        return self._signal.shape()
    
    def __getattr__(self, name):
        return getattr(self._signal, name)
    
    def __bool__(self): return self._signal.__bool__()
    def __pos__(self): return self._signal.__pos__()
    def __invert__(self): return self._signal.__invert__()
    def __neg__(self): return self._signal.__neg__()
    def __add__(self, other): return self._signal.__add__(other)
    def __radd__(self, other): return self._signal.__radd__(other)
    def __sub__(self, other): return self._signal.__sub__(other)
    def __rsub__(self, other): return self._signal.__rsub__(other)
    def __mul__(self, other): return self._signal.__mul__(other)
    def __rmul__(self, other): return self._signal.__rmul__(other)
    def __mod__(self, other): return self._signal.__mod__(other)
    def __rmod__(self, other): return self._signal.__rmod__(other)
    def __floordiv__(self, other): return self._signal.__floordiv__(other)
    def __rfloordiv__(self, other): return self._signal.__rfloordiv__(other)
    def __lshift__(self, other): return self._signal.__lshift__(other)
    def __rlshift__(self, other): return self._signal.__rlshift__(other)
    def __rshift__(self, other): return self._signal.__rshift__(other)
    def __rrshift__(self, other): return self._signal.__rrshift__(other)
    def __and__(self, other): return self._signal.__and__(other)
    def __rand__(self, other): return self._signal.__rand__(other)
    def __xor__(self, other): return self._signal.__xor__(other)
    def __rxor__(self, other): return self._signal.__rxor__(other)
    def __or__(self, other): return self._signal.__or__(other)
    def __ror__(self, other): return self._signal.__ror__(other)
    def __eq__(self, other): return self._signal.__eq__(other)
    def __ne__(self, other): return self._signal.__ne__(other)
    def __lt__(self, other): return self._signal.__lt__(other)
    def __le__(self, other): return self._signal.__le__(other)
    def __gt__(self, other): return self._signal.__gt__(other)
    def __ge__(self, other): return self._signal.__ge__(other)
    def __abs__(self): return self._signal.__abs__()
    def __len__(self): return self._signal.__len__()
    def __getitem__(self, key): return self._signal.__getitem__(key)


class StatusSignal(ValueCastable, _Csr):
    """ Just a Signal. Indicator, that it is for communicating the state to the outside world (i.e. can be read but not written from the outside)
        Is mapped as a CSR in case the design is build with a SocPlatform.
    """

    def __init__(self, shape=None, *, address=None, read_strobe=None, src_loc_at=0, **kwargs):
        self._signal = Signal(shape, src_loc_at=src_loc_at+1, **kwargs, )

        self._address = Address.parse(address)
        self._read_strobe = read_strobe

    def as_value(self):
        return self._signal
    
    def shape(self):
        return self._signal.shape()
    
    def __getattr__(self, name):
        return getattr(self._signal, name)
    
    def __bool__(self): return self._signal.__bool__()
    def __pos__(self): return self._signal.__pos__()
    def __invert__(self): return self._signal.__invert__()
    def __neg__(self): return self._signal.__neg__()
    def __add__(self, other): return self._signal.__add__(other)
    def __radd__(self, other): return self._signal.__radd__(other)
    def __sub__(self, other): return self._signal.__sub__(other)
    def __rsub__(self, other): return self._signal.__rsub__(other)
    def __mul__(self, other): return self._signal.__mul__(other)
    def __rmul__(self, other): return self._signal.__rmul__(other)
    def __mod__(self, other): return self._signal.__mod__(other)
    def __rmod__(self, other): return self._signal.__rmod__(other)
    def __floordiv__(self, other): return self._signal.__floordiv__(other)
    def __rfloordiv__(self, other): return self._signal.__rfloordiv__(other)
    def __lshift__(self, other): return self._signal.__lshift__(other)
    def __rlshift__(self, other): return self._signal.__rlshift__(other)
    def __rshift__(self, other): return self._signal.__rshift__(other)
    def __rrshift__(self, other): return self._signal.__rrshift__(other)
    def __and__(self, other): return self._signal.__and__(other)
    def __rand__(self, other): return self._signal.__rand__(other)
    def __xor__(self, other): return self._signal.__xor__(other)
    def __rxor__(self, other): return self._signal.__rxor__(other)
    def __or__(self, other): return self._signal.__or__(other)
    def __ror__(self, other): return self._signal.__ror__(other)
    def __eq__(self, other): return self._signal.__eq__(other)
    def __ne__(self, other): return self._signal.__ne__(other)
    def __lt__(self, other): return self._signal.__lt__(other)
    def __le__(self, other): return self._signal.__le__(other)
    def __gt__(self, other): return self._signal.__gt__(other)
    def __ge__(self, other): return self._signal.__ge__(other)
    def __abs__(self): return self._signal.__abs__()
    def __len__(self): return self._signal.__len__()
    def __getitem__(self, key): return self._signal.__getitem__(key)



class EventReg(_Csr):  # TODO: bikeshed name
    """ A "magic" register, that doesnt have to be backed by a real register. Useful for implementing resets,
    fifo interfaces, ...
    The logic generated by the handle_read and handle_write hooks is part of the platform defined BusSlave and runs in its clockdomain.
    """

    def __init__(self, bits=None, address=None):
        super().__init__()
        assert address is not None or bits is not None
        if bits is not None:
            assert bits <= 32, "EventReg access would not be atomic!"
        self._bits = bits
        self._address = Address.parse(address)

        def handle_read(m, data, read_done):
            read_done(Response.ERR)

        self.handle_read = handle_read

        def handle_write(m, data, write_done):
            write_done(Response.ERR)

        self.handle_write = handle_write

    def __len__(self):
        if self._address is not None:
            return self._address.bit_len
        return self._bits

# TODO: make this not Elaboratable, but instead add API to _Csr to add statements to the peripheral connector module
class PulseReg(EventReg, Elaboratable):  # TODO: replace with _write_strobe?
    """A register that generates one cycle wide pulses when ones are written. The pulses happen in the CSR domain.
    Use a PulseSynchronizer to get one cycle wide pulses in another domain, so long as its clock speed is not slower than the CSR domain.
    """

    def __init__(self, bits):
        super().__init__(bits=bits)

        self.pulse = Signal(bits)
        self._write_val = Signal(bits)

        def handle_read(m, data, read_done):
            m.d.sync += data.eq(0)
            read_done(Response.OK)

        def handle_write(m, data, write_done):
            m.d.comb += self._write_val.eq(data)
            write_done(Response.OK)

        self.handle_read = handle_read
        self.handle_write = handle_write

    def elaborate(self, platform):
        m = Module()

        from ..soc import PERIPHERAL_DOMAIN
        m.d[PERIPHERAL_DOMAIN] += self.pulse.eq(self._write_val)

        return m
