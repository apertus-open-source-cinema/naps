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
    @staticmethod
    def like(model, master=None, lite=None):
        """
        Create an AxiInterface shaped like a given model.
        :type model: AxiInterface
        :param model: the model after which the axi port should be created
        :type master: bool
        :param master: overrides the master property of the model
        :param lite: overrides the lite property of the model. Only works for creating an AXI lite inteface from an AXI full interface.
        :return:
        """
        if lite is not None:
            assert model.is_master or lite, "cant make up id_bits out of thin air"

        return AxiInterface(
            addr_bits=model.addr_bits,
            data_bits=model.data_bits,
            lite=lite if lite is not None else model.is_lite,
            id_bits=None if (lite is not None and lite) else model.id_bits,
            master=master if master is not None else model.is_master
        )

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
            self.num_slaves = 0
        self.addr_bits = addr_bits
        self.data_bits = data_bits
        self.is_lite = lite
        self.id_bits = id_bits

    def connect_slave(self, slave):
        """
        Connects an AXI slave to this AXI master. Can only be used a single time since every other case requires some kind
        of AXI inteconnect.

        usage example:
        >>> stmts += master.connect_slave(slave)

        :type slave: AxiInterface
        :param slave: the slave to connect.
        :returns the list of
        """
        assert self.is_master
        master = self
        assert not slave.is_master
        assert master.is_lite == slave.is_lite
        full = not master.is_lite
        assert self.num_slaves == 0, "Only one Slave can be added to an AXI master without an interconnect"

        stmts = []

        stmts += [slave.read_address.value.eq(master.read_address.value)]
        stmts += [slave.read_address.valid.eq(master.read_address.valid)]
        if full:
            stmts += [slave.read_address.id.eq(master.read_address.id)]
        stmts += [master.read_address.ready.eq(slave.read_address.ready)]

        stmts += [master.read_data.value.eq(slave.read_data.value)]
        stmts += [master.read_data.valid.eq(slave.read_data.valid)]
        stmts += [master.read_data.resp.eq(slave.read_data.resp)]
        if full:
            stmts += [master.read_data.id.eq(slave.read_data.id)]
        stmts += [slave.read_data.ready.eq(master.read_data.ready)]

        stmts += [slave.write_address.value.eq(master.write_address.value)]
        stmts += [slave.write_address.valid.eq(master.write_address.valid)]
        if full:
            stmts += [slave.write_address.id.eq(master.write_address.id)]
        stmts += [master.write_address.ready.eq(slave.write_address.ready)]

        stmts += [slave.write_data.value.eq(master.write_data.value)]
        stmts += [slave.write_data.valid.eq(master.write_data.valid)]
        stmts += [slave.write_data.strb.eq(master.write_data.strb)]
        if full:
            stmts += [slave.write_data.id.eq(slave.write_data.id)]
        stmts += [master.write_data.ready.eq(slave.write_data.ready)]

        stmts += [master.write_response.resp.eq(slave.write_response.resp)]
        stmts += [master.write_response.valid.eq(slave.write_response.valid)]
        if full:
            stmts += [master.write_response.id.eq(slave.write_response.id)]
        stmts += [slave.write_response.ready.eq(master.write_response.ready)]

        self.num_slaves += 1
        return stmts
