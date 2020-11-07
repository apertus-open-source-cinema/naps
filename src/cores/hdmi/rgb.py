from nmigen import Signal

from util.packed_struct import PackedStruct


class Rgb(PackedStruct):
    r = Signal(8)
    g = Signal(8)
    b = Signal(8)