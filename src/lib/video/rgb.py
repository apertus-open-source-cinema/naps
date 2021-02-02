from nmigen import *

from lib.data_structure.packed_struct import packed_struct


def gen_rgb_n(bits):
    @packed_struct
    class RGB:
        r: unsigned(bits)
        g: unsigned(bits)
        b: unsigned(bits)

        def brightness(self):
            return self.r + self.g + self.b

    return RGB


RGB24 = gen_rgb_n(8)
