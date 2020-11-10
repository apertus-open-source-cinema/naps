from nmigen import Signal

from lib.data_structure.packed_struct import PackedStruct


class RGB(PackedStruct):
    def __init__(self, bits=8, name=None, src_loc_at=1):
        super().__init__(name, src_loc_at + 1)
        self.r = Signal(bits)
        self.g = Signal(bits)
        self.b = Signal(bits)