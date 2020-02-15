from nmigen import *
from nmigen.hdl.rec import Direction
from enum import Enum


class Response(Enum):
    OKAY = 0b00
    EXOKAY = 0b01
    SLVERR = 0b10
    DECERR = 0b11


class BurstType(Enum):
    FIXED = 0b00
    INCR = 0b01
    WRAP = 0b10


# TODO(robin): are these directions right????
def axi_channel(payload, master_to_slave):
    if master_to_slave:
        return payload + [("valid", 1, Direction.FANIN), ("ready", 1, Direction.FANOUT)]
    else:
        return payload + [("valid", 1, Direction.FANOUT), ("ready", 1, Direction.FANIN)]


# read address or write address channel
def address_channel(*, addr_bits, lite, id_bits=None):
    layout = axi_channel([
        ("addr", addr_bits, Direction.FANIN),
    ], True)

    if not lite:
        assert id_bits is not None, "id_bits is mandatory for full axi"
        layout += [
            ("id", id_bits, Direction.FANIN),
            ("burst", 2, Direction.FANIN),
            ("len", 4, Direction.FANIN),
            ("size", 2, Direction.FANIN),
            ("prot", 3, Direction.FANIN)
        ]
    else:
        assert id_bits is None, "id_bits specified for axi lite. axi lite doesnt have transaction ids"

    return layout


# read data or write data channel (for read data channel set read to true)
def data_channel(*, data_bits, lite, read, id_bits=None):
    if read:
        direction = Direction.FANIN
    else:
        direction = Direction.FANOUT

    if lite:
        assert data_bits == 32, "xilinx zynq only support 32bit data widths in axi lite mode"

    layout = axi_channel([
        ("data", data_bits, direction),
    ], ~read)

    if read:
        layout += [("resp", 2, direction)]
    else:
        layout += [("strb", 4, direction)]  # slaves can elect to ignore strobe in axi lite

    if not lite:
        assert id_bits is not None, "id_bits is mandatory for full axi"
        layout += [
            ("id", id_bits, direction),
            ("last", 1, direction),
        ]
    else:
        assert id_bits is None, "id_bits specified for axi lite. axi lite doesnt have transaction ids"

    return layout


def write_response_channel(*, lite, id_bits=None):
    layout = axi_channel([
        ("resp", 2, Direction.FANOUT)
    ], False)

    if not lite:
        assert id_bits is not None, "id_bits is mandatory for full axi"
        layout += [
            ("id", id_bits, Direction.FANOUT),
        ]
    else:
        assert id_bits is None, "id_bits specified for axi lite. axi lite doesnt have transaction ids"

    return layout


class Interface(Record):
    def __init__(self, *, addr_bits, data_bits, lite, id_bits=None):
        layout = [
            ("read_address", address_channel(addr_bits=addr_bits, lite=lite, id_bits=id_bits)),
            ("write_address", address_channel(addr_bits=addr_bits, lite=lite, id_bits=id_bits)),
            ("read_data", data_channel(data_bits=data_bits, read=True, lite=lite, id_bits=id_bits)),
            ("write_data", data_channel(data_bits=data_bits, read=False, lite=lite, id_bits=id_bits)),
            ("write_response", write_response_channel(lite=lite, id_bits=id_bits)),
        ]

        super().__init__(layout, src_loc_at=1)


