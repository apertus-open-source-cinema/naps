from contextlib import contextmanager

from nmigen import *
from enum import Enum

from util.bundle import Bundle
from util.nmigen import connect_together


class Response(Enum):
    OKAY = 0b00
    EXOKAY = 0b01
    SLVERR = 0b10
    DECERR = 0b11


class BurstType(Enum):
    FIXED = 0b00
    INCR = 0b01
    WRAP = 0b10


class AddressChannel(Bundle):
    def __init__(self, addr_bits, lite, id_bits):
        super().__init__()

        self.ready = Signal()
        self.valid = Signal()
        self.value = Signal(addr_bits)

        if not lite:
            self.id = Signal(id_bits)
            self.burst = Signal(2)
            self.len = Signal(4)
            self.size = Signal(2)
            self.prot = Signal(3)


class DataChannel(Bundle):
    def __init__(self, data_bits, read, lite, id_bits):
        super().__init__()

        self.ready = Signal()
        self.valid = Signal()
        self.value = Signal(data_bits)
        if read:
            self.resp = Signal(2)
        else:
            self.strb = Signal(4)

        if not lite:
            self.last = Signal()
            self.id = Signal(id_bits)


class WriteResponseChannel(Bundle):
    def __init__(self, lite, id_bits):
        super().__init__()

        self.ready = Signal()
        self.valid = Signal()
        self.resp = Signal(2)

        if not lite:
            self.id = Signal(id_bits)


class AxiInterface(Bundle):
    def __init__(self, *, addr_bits, data_bits, master, lite, id_bits=None):
        """
        Constructs a Record holding all the signals for axi (lite)

        :param addr_bits: the number of bits the address signal has.
        :param data_bits: the number of bits the
        :param lite: whether to construct an AXI lite or full bus.
        :param id_bits: the number of bits for the id signal of full axi. do not specify if :param lite is True.
        :param master: whether the record represents a master or a slave
        """
        super().__init__()

        if id_bits:
            assert not lite, "there is no id tracking with axi lite"
        if lite:
            assert id_bits is None

        # signals
        lite_args = {"lite": lite, "id_bits": id_bits}
        self.read_address = AddressChannel(addr_bits, **lite_args)
        self.read_data = DataChannel(data_bits, read=True, **lite_args)

        self.write_address = AddressChannel(addr_bits, **lite_args)
        self.write_data = DataChannel(data_bits, read=False, **lite_args)
        self.write_response = WriteResponseChannel(**lite_args)

        # metadata
        self.is_master = master
        if master:
            self.clk = Signal()
            self.interconnect = None
            self.num_slaves = 0
        self.addr_bits = addr_bits
        self.data_bits = data_bits
        self.is_lite = lite
        self.id_bits = id_bits

    def get_interconnect_submodule(self):
        assert self.is_master
        if not self.interconnect:
            self.interconnect = Module()
        return self.interconnect

    def connect_slave(self, slave):
        """
        Connects an AXI slave to this AXI master. Calling this method requires self to be an AXI master and slave to be
        a slave. Also both busses must be AXI lite (at the moment). This function returns an interconnect, that MUST be
        added to the parents submodules
        :type slave: AxiInterface
        :param slave: the slave to connect.
        :returns the module to connect the slaves
        """
        assert self.is_master
        master = self
        assert not slave.is_master
        assert master.is_lite == slave.is_lite
        full = not master.is_lite

        if full and self.num_slaves != 0:
            raise NotImplemented("Interconnect logic is unimplemented for full axi")

        m = self.get_interconnect_submodule()

        if self.num_slaves != 0:
            def a(**kwargs):
                assert len(kwargs.keys()) == 1
                name, signal = list(kwargs.items())[0]
                return connect_together(signal, "{}_{}".format(repr(self), name), operation='&')

            conditional = m.If
        else:
            # if we are the first slave, jut connect everything stupid together
            def a(**kwargs):
                assert len(kwargs.keys()) == 1
                name, signal = list(kwargs.items())[0]
                return signal

            @contextmanager
            def conditional(ignored_condition):
                try:
                    yield
                finally:
                    pass

        m.d.comb += slave.read_address.value.eq(master.read_address.value)
        m.d.comb += slave.read_address.valid.eq(master.read_address.valid)
        if full:
            m.d.comb += slave.read_address.id.eq(master.read_address.id)
        m.d.comb += master.read_address.ready.eq(a(rar=slave.read_address.ready))

        with conditional(slave.read_data.valid):
            m.d.comb += master.read_data.value.eq(slave.read_data.value)
            m.d.comb += master.read_data.valid.eq(slave.read_data.valid)
            m.d.comb += master.read_data.resp.eq(slave.read_data.resp)
            if full:
                m.d.comb += master.read_data.id.eq(slave.read_data.id)
            m.d.comb += slave.read_data.ready.eq(master.read_data.ready)

        m.d.comb += slave.write_address.value.eq(master.write_address.value)
        m.d.comb += slave.write_address.valid.eq(master.write_address.valid)
        if full:
            m.d.comb += slave.write_address.id.eq(master.write_address.id)
        m.d.comb += master.write_address.ready.eq(a(war=slave.write_address.ready))

        with conditional(slave.write_data.valid):
            m.d.comb += slave.write_data.value.eq(master.write_data.value)
            m.d.comb += slave.write_data.valid.eq(master.write_data.valid)
            m.d.comb += slave.write_data.strb.eq(master.write_data.strb)
            if full:
                m.d.comb += slave.write_data.id.eq(slave.write_data.id)
            m.d.comb += master.write_data.ready.eq(slave.write_data.ready)

        with conditional(slave.write_response.valid):
            m.d.comb += master.write_response.resp.eq(slave.write_response.resp)
            m.d.comb += master.write_response.valid.eq(slave.write_response.valid)
            if full:
                m.d.comb += master.write_response.id.eq(slave.write_response.id)
            m.d.comb += slave.write_response.ready.eq(master.write_response.ready)

        self.num_slaves += 1
