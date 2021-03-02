from nmigen import *
from naps import packed_struct

__all__ = ["RGB24", "RGB565"]


def gen_rgb_n(r_bits, g_bits, b_bits):
    @packed_struct
    class RGB:
        r: unsigned(r_bits)
        g: unsigned(g_bits)
        b: unsigned(b_bits)

        def brightness(self):
            return self.r + self.g + self.b

    return RGB


RGB24 = gen_rgb_n(8, 8, 8)
RGB565 = gen_rgb_n(5, 6, 5)
