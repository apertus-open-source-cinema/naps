from functools import reduce
from operator import add

from nmigen import *

control_tokens = [0b1101010100, 0b0010101011, 0b0101010100, 0b1010101011]


class Encoder(Elaboratable):
    def __init__(self, data, control, data_enable):
        self.data = data
        self.control = control
        self.data_enable = data_enable

        self.out = Signal(10)

    def elaborate(self, platform):
        m = Module()

        # stage 1 - count number of 1s in data
        d = Signal(8)
        n1d = Signal(range(9))
        m.d.sync += [
            n1d.eq(reduce(add, [self.data[i] for i in range(8)])),
            d.eq(self.data)
        ]

        # stage 2 - add 9th bit
        q_m = Signal(9)
        q_m8_n = Signal()
        m.d.comb += q_m8_n.eq((n1d > 4) | ((n1d == 4) & ~d[0]))

        m.d.sync += q_m[0].eq(d[0])

        curval = d[0]
        for i in range(1, 8):
            curval = curval ^ d[i] ^ q_m8_n
            m.d.sync += q_m[i].eq(curval)
        m.d.sync += q_m[8].eq(~q_m8_n)

        # stage 3 - count number of 1s and 0s in q_m[:8]
        q_m_r = Signal(9)
        n0q_m = Signal(range(9))
        n1q_m = Signal(range(9))
        m.d.sync += [
            n0q_m.eq(reduce(add, [~q_m[i] for i in range(8)])),
            n1q_m.eq(reduce(add, [q_m[i] for i in range(8)])),
            q_m_r.eq(q_m)
        ]

        # stage 4 - final encoding
        cnt = Signal(Shape(6, True))

        s_c = self.control
        s_de = self.data_enable
        for p in range(3):
            new_c = Signal(2)
            new_de = Signal()
            m.d.sync += new_c.eq(s_c), new_de.eq(s_de)
            s_c, s_de = new_c, new_de

        with m.If(s_de):
            with m.If((cnt == 0) | (n1q_m == n0q_m)):
                m.d.sync += [
                    self.out[9].eq(~q_m_r[8]),
                    self.out[8].eq(q_m_r[8])
                ]
                with m.If(q_m_r[8]):
                    m.d.sync += [
                        self.out[:8].eq(q_m_r[:8]),
                        cnt.eq(cnt + n1q_m - n0q_m)
                    ]
                with m.Else():
                    m.d.sync += [
                        self.out[:8].eq(~q_m_r[:8]),
                        cnt.eq(cnt + n0q_m - n1q_m)
                    ]
            with m.Else():
                with m.If((~cnt[5] & (n1q_m > n0q_m)) | (cnt[5] & (n0q_m > n1q_m))):
                    m.d.sync += [
                        self.out[9].eq(1),
                        self.out[8].eq(q_m_r[8]),
                        self.out[:8].eq(~q_m_r[:8]),
                        cnt.eq(cnt + Cat(0, q_m_r[8]) + n0q_m - n1q_m)
                    ]
                with m.Else():
                    m.d.sync += [
                        self.out[9].eq(0),
                        self.out[8].eq(q_m_r[8]),
                        self.out[:8].eq(q_m_r[:8]),
                        cnt.eq(cnt - Cat(0, ~q_m_r[8]) + n1q_m - n0q_m)
                    ]
        with m.Else():
            m.d.sync += [
                self.out.eq(Array(control_tokens)[s_c]),
                cnt.eq(0)
            ]

        return m