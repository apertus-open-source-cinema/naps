from nmigen import *

"""
nMigen port of the following VHDL code, retrieved from
https://github.com/daveshah1/prjtrellis-dvi/blob/master/hdl/tmds_encoder.vhd
Original source seems to be unavailable.
Updated to match implementation from
https://www.digikey.com/eewiki/pages/viewpage.action?pageId=36569119#TMDSEncoder%28VHDL%29-AdditionalInformation
Copyright (C) 2020 Konrad Beckmann
Copyright (C) 2012 Mike Field <hamster@snap.net.nz>
License from the original source:
----------------------------------------------------------------------------------
-- Engineer: Mike Field <hamster@snap.net.nz>
-- 
-- Description: TMDS Encoder 
--     8 bits colour, 2 control bits and one blanking bits in
--       10 bits of TMDS encoded data out
--     Clocked at the pixel clock
--
----------------------------------------------------------------------------------
-- See: http://hamsterworks.co.nz/mediawiki/index.php/Dvid_test
--      http://hamsterworks.co.nz/mediawiki/index.php/FPGA_Projects
--
-- Copyright (c) 2012 Mike Field <hamster@snap.net.nz>
--
-- Permission is hereby granted, free of charge, to any person obtaining a copy
-- of this software and associated documentation files (the "Software"), to deal
-- in the Software without restriction, including without limitation the rights
-- to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
-- copies of the Software, and to permit persons to whom the Software is
-- furnished to do so, subject to the following conditions:
--
-- The above copyright notice and this permission notice shall be included in
-- all copies or substantial portions of the Software.
--
-- THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
-- IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
-- FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
-- AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
-- LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
-- OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
-- THE SOFTWARE.
--
"""


class TmdsEncoder(Elaboratable):
    def __init__(self, data, c, active):
        assert(data.shape().width == 8)
        assert(c.shape().width == 2)
        assert(active.shape().width == 1)

        self.data = data
        self.c = c
        self.blank = ~active
        self.out = Signal(10)

    def elaborate(self, platform):
        m = Module()

        data = self.data

        xored = Signal(9)
        m.d.comb += xored.eq(Cat(
            data[0],
            data[1] ^ xored[0],
            data[2] ^ xored[1],
            data[3] ^ xored[2],
            data[4] ^ xored[3],
            data[5] ^ xored[4],
            data[6] ^ xored[5],
            data[7] ^ xored[6],
            1
        ))

        xnored = Signal(9)
        m.d.comb += xnored.eq(Cat(
            data[0],
            ~(data[1] ^ xnored[0]),
            ~(data[2] ^ xnored[1]),
            ~(data[3] ^ xnored[2]),
            ~(data[4] ^ xnored[3]),
            ~(data[5] ^ xnored[4]),
            ~(data[6] ^ xnored[5]),
            ~(data[7] ^ xnored[6]),
            0
        ))

        ones = Signal(4)
        m.d.comb += ones.eq(sum(data))

        data_word = Signal(9)
        data_word_inv = Signal(9)
        disparity = Signal(Shape(4, signed=True))

        with m.If((ones > 4) | ((ones == 4) & (data[0] == 0))):
            m.d.sync += data_word.eq(xnored)
            m.d.sync += data_word_inv.eq(~xnored)
        with m.Else():
            m.d.sync += data_word.eq(xored)
            m.d.sync += data_word_inv.eq(~xored)

        # diff_q_m holds the difference between the number of ones and zeros
        diff_q_m = Signal(Shape(4, signed=True))
        data_word_ones = Signal(4)
        m.d.comb += data_word_ones.eq(sum(data_word[:8]))
        m.d.comb += diff_q_m.eq(sum(data_word[:8]) - sum(~data_word[:8]))

        with m.If(self.blank):
            with m.Switch(self.c):
                with m.Case(0b00):
                    m.d.sync += self.out.eq(0b1101010100)
                with m.Case(0b01):
                    m.d.sync += self.out.eq(0b0010101011)
                with m.Case(0b10):
                    m.d.sync += self.out.eq(0b0101010100)
                with m.Case(0b11):
                    m.d.sync += self.out.eq(0b1010101011)
            m.d.sync += disparity.eq(0)

        with m.Else():
            with m.If((disparity == 0) | (data_word_ones == 4)):
                with m.If(data_word[8] == 0):
                    m.d.sync += self.out.eq(Cat(data_word_inv[:8], data_word[8], ~data_word[8]))
                    m.d.sync += disparity.eq(disparity - diff_q_m)
                with m.Else():
                    m.d.sync += self.out.eq(Cat(data_word[:9], ~data_word[8]))
                    m.d.sync += disparity.eq(disparity + diff_q_m)
            with m.Else():
                with m.If(((disparity > 0) & (data_word_ones > 4)) |
                            ((disparity < 0) & (data_word_ones < 4))):
                    m.d.sync += self.out.eq(Cat(data_word_inv[:8], data_word[8], 0b1))
                    with m.If(data_word[8] == 0):
                        m.d.sync += disparity.eq(disparity - diff_q_m)
                    with m.Else():
                        m.d.sync += disparity.eq(disparity - diff_q_m + 2)
                with m.Else():
                    m.d.sync += self.out.eq(Cat(data_word[:9], 0b0))
                    with m.If(data_word[8] == 0):
                        m.d.sync += disparity.eq(disparity + diff_q_m - 2)
                    with m.Else():
                        m.d.sync += disparity.eq(disparity + diff_q_m)

        return m


class Decoder(Elaboratable):
    def __init__(self, data_in, data_out, c, active_data):
        assert(data_in.shape().width == 10)
        assert(data_out.shape().width == 8)
        assert(c.shape().width == 2)
        assert(active_data.shape().width == 1)

        self.data_in = data_in
        self.data_out = data_out
        self.c = c
        self.active_data = active_data

    def elaborate(self, platform):
        m = Module()

        data_in = self.data_in
        data_out = self.data_out
        c = self.c
        active_data = self.active_data

        data_delayed = Signal(10)
        sometimes_inverted = Signal(9)
        next_c = Signal(2)
        next_active_data = Signal()

        m.d.sync += c.eq(next_c)
        m.d.sync += active_data.eq(next_active_data)

        with m.If(next_active_data == 0):
            m.d.sync += data_out.eq(0)
        with m.Elif(sometimes_inverted[8] == 1):
            m.d.sync += data_out.eq(Cat(
                sometimes_inverted[0],
                sometimes_inverted[1] ^ sometimes_inverted[0],
                sometimes_inverted[2] ^ sometimes_inverted[1],
                sometimes_inverted[3] ^ sometimes_inverted[2],
                sometimes_inverted[4] ^ sometimes_inverted[3],
                sometimes_inverted[5] ^ sometimes_inverted[4],
                sometimes_inverted[6] ^ sometimes_inverted[5],
                sometimes_inverted[7] ^ sometimes_inverted[6],
            ))
        with m.Else():
            m.d.sync += data_out.eq(Cat(
                sometimes_inverted[0],
                ~(sometimes_inverted[1] ^ sometimes_inverted[0]),
                ~(sometimes_inverted[2] ^ sometimes_inverted[1]),
                ~(sometimes_inverted[3] ^ sometimes_inverted[2]),
                ~(sometimes_inverted[4] ^ sometimes_inverted[3]),
                ~(sometimes_inverted[5] ^ sometimes_inverted[4]),
                ~(sometimes_inverted[6] ^ sometimes_inverted[5]),
                ~(sometimes_inverted[7] ^ sometimes_inverted[6]),
            ))

        with m.If(data_delayed[9] == 1):
            m.d.sync += sometimes_inverted.eq(Cat(~data_delayed[:8], data_delayed[8]))
        with m.Else():
            m.d.sync += sometimes_inverted.eq(data_delayed[:9])

        with m.Switch(data_in):
            with m.Case(0b0010101011):
                m.d.sync += next_c.eq(0b01)
                m.d.sync += next_active_data.eq(0)
            with m.Case(0b1101010100):
                m.d.sync += next_c.eq(0b00)
                m.d.sync += next_active_data.eq(0)
            with m.Case(0b0101010100):
                m.d.sync += next_c.eq(0b10)
                m.d.sync += next_active_data.eq(0)
            with m.Case(0b1010101011):
                m.d.sync += next_c.eq(0b00)
                m.d.sync += next_active_data.eq(0)
            with m.Default():
                m.d.sync += next_c.eq(0b00)
                m.d.sync += next_active_data.eq(1)

        m.d.sync += data_delayed.eq(data_in)

        return m
