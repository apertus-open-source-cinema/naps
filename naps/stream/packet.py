from amaranth import Signal, Shape
from amaranth.lib import data

class Packet(data.StructLayout):
    def __init__(self, payload_shape):
        super().__init__({
                "p": payload_shape,
                "last": 1
        })

def out_of_band_signals(struct: data.Struct):
    oob = []

    while isinstance(struct.shape(), Packet):
        oob.append(struct.last)
        struct = struct.p

    return oob

def real_payload(struct: data.Struct):
    while isinstance(struct.shape(), Packet):
        struct = struct.p
    return struct

def substitute_payload(shape: Shape, substitute: Shape):
    ret = substitute
    while isinstance(shape, Packet):
        shape = shape["p"].shape
        ret = Packet(ret)

    return ret
