from nmigen import *

from ..tmds import tmds_control_tokens

class TmdsEncoder(Elaboratable):
    def __init__(self, data, control, data_enable):
        self.data = data
        self.control = control
        self.data_enable = data_enable

        self.out = Signal(10)

    def elaborate(self, platform):
        m = Module()

        # stage 1 - count number of 1s in data
        data = Signal(8)
        ones_in_data = Signal(range(9))
        m.d.sync += [
            ones_in_data.eq(sum(self.data[0:8])),
            data.eq(self.data)
        ]

        # stage 2 - add 9th bit
        q_m = Signal(9)
        q_m8_n = Signal()
        m.d.comb += q_m8_n.eq((ones_in_data > 4) | ((ones_in_data == 4) & ~data[0]))

        m.d.sync += q_m[0].eq(data[0])

        curval = data[0]
        for i in range(1, 8):
            curval = curval ^ data[i] ^ q_m8_n
            m.d.sync += q_m[i].eq(curval)
        m.d.sync += q_m[8].eq(~q_m8_n)

        # stage 3 - count number of 1s and 0s in q_m[:8]
        q_m_r = Signal(9)
        n0q_m = Signal(range(9))
        n1q_m = Signal(range(9))
        m.d.sync += [
            n0q_m.eq(sum(~q_m[0:8])),
            n1q_m.eq(sum(q_m[0:8])),
            q_m_r.eq(q_m)
        ]

        # stage 4 - final encoding
        disparity = Signal(signed(6))

        # match latency of control and data enable
        control = self.control
        data_enable = self.data_enable
        for p in range(3):
            new_c = Signal(2)
            new_de = Signal()
            m.d.sync += new_c.eq(control), new_de.eq(data_enable)
            control, data_enable = new_c, new_de

        with m.If(data_enable):
            with m.If((disparity == 0) | (n1q_m == n0q_m)):
                m.d.sync += [
                    self.out[9].eq(~q_m_r[8]),
                    self.out[8].eq(q_m_r[8])
                ]
                with m.If(q_m_r[8]):
                    m.d.sync += [
                        self.out[:8].eq(q_m_r[:8]),
                        disparity.eq(disparity + n1q_m - n0q_m)
                    ]
                with m.Else():
                    m.d.sync += [
                        self.out[:8].eq(~q_m_r[:8]),
                        disparity.eq(disparity + n0q_m - n1q_m)
                    ]
            with m.Else():
                with m.If((~disparity[5] & (n1q_m > n0q_m)) | (disparity[5] & (n0q_m > n1q_m))):
                    m.d.sync += [
                        self.out[9].eq(1),
                        self.out[8].eq(q_m_r[8]),
                        self.out[:8].eq(~q_m_r[:8]),
                        disparity.eq(disparity + Cat(0, q_m_r[8]) + n0q_m - n1q_m)
                    ]
                with m.Else():
                    m.d.sync += [
                        self.out[9].eq(0),
                        self.out[8].eq(q_m_r[8]),
                        self.out[:8].eq(q_m_r[:8]),
                        disparity.eq(disparity - Cat(0, ~q_m_r[8]) + n1q_m - n0q_m)
                    ]
        with m.Else():
            m.d.sync += [
                self.out.eq(Array(tmds_control_tokens)[control]),
                disparity.eq(0)
            ]

        return m