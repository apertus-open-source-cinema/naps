from amaranth import *
from amaranth.lib import data

__all__ = ["RGB24", "RGB565"]


class RGB(data.StructLayout):
    r: Signal
    b: Signal
    g: Signal

    def __init__(self, r_bits, g_bits, b_bits):
        super().__init__({
            "r": r_bits,
            "g": g_bits,
            "b": b_bits,
        })

    def brightness(self):
        return self.r + self.g + self.b

RGB24 = RGB(8, 8, 8)
RGB565 = RGB(5, 6, 5)
