from nmigen import *


def gen_rgb_n(bits):
    class RGB:
        r: unsigned(bits)
        g: unsigned(bits)
        b: unsigned(bits)

        def brightness(self):
            return self.r + self.g + self.b

    return RGB


RGB24 = gen_rgb_n(8)
