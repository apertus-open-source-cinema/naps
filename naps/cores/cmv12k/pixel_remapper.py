# remaps the cmv12k output lanes into an ImageStream with subsequent pixels
# the raw lane output of the cmv12k is a bit wired

from typing import List

from amaranth import *
from amaranth.utils import bits_for
from naps import BasicStream, packed_struct
from naps.cores import ImageStream, BufferedSyncStreamFIFO
from naps.util.past import Changed


__all__ = ["Cmv12kPixelRemapper"]


# cmv12k pixel remapping:
# this takes the input straight of the sensor in the order
# [top side channels, bottom side channels]
# we only consider two sided readout mode here
# First the cmv12k can be configured to used [1, 2, 4, 8, 16, 32] channels *per side* (n_channel)
# the cmv12k then outputs pixels belonging to a single row (which has a width of 4096 pixels (row_width)) in sequential packets of `pixels_per_channel := row_width / n_channel` pixels, where whole packets
# are striped across the channels (for one side). Finally the clock we are using has double the rate of the pixel data, so only every second clock cycle gives us data
# For example for `n_channel = 16` (the numbers in the table are the index in row of the pixel transmitted):
# |  clock -> |    0 | 1 |    2 | ... |  510 |
# | channel ∨ |      |   |      |     |      |
# |-----------+------+---+------+-----+------|
# |         0 |    0 | - |    1 |     |  255 |
# |         1 |  256 | - |  257 |     |  511 |
# |         2 |  512 | - |  513 |     |  767 |
# |       ... |      | - |      |     |      |
# |        15 | 3840 | - | 3841 |     | 4095 |
# This core remaps the pixels so the output is striped per pixel across the channels, not per packet, like so:
# |  clock -> |  0 |  1 | ... |  255 |
# | channel ∨ |    |    |     |      |
# |-----------+----+----+-----+------|
# |         0 |  0 | 16 |     | 4080 |
# |         1 |  1 | 17 |     | 4081 |
# |         2 |  2 | 18 |     | 4082 |
# |       ... |    |    |     |      |
# |         7 | 15 | 31 |     | 4095 |
# Note, that we have half as many output channels as input channels. We provide valid data on every clock cycle. (Almost, there will be some cycles where the data is not valid).
# It should be immediately obvious that for this remapping to be possible some amount of pixels have to be stored. The obvious choice for this are the BRAM part of basically any FPGA arch.
# Lets first look at the remapping we need to do for one of the sides, and then look at how the other side ties into this.
# The following discussion will focus on the 7series FPGAs. On 7series, a BRAM can in SDP-mode have a port width of at most 36 bits. This means we can at most write 36 bits in a single cycle to a BRAM.
# This immediately gives a constraint on the number of BRAMs we need. We have a input (and of course output) bandwidth of (12 bits (per pixel) * n_channel) every two clock cycles.
# We need to be able to have atleast as much input bandwidth to the BRAMs: `n_brams >= n_channel / 6`, giving a lower bound of 3 BRAMs in the case of `n_channel = 16`.
# On the output side we have atleast the same output bandwidth. The output of a single cycle is always a sequence to `n_channel` sequential pixels. So for a single clock cycle we cannot pack the input pixels of multiple channels into a single BRAM (if we would do this, we would not be able to read all the pixels we need for a single cycle in a single cycle, as there would be pixels not belonging to the sequence we need packed in with the ones we need).
# This means, if we want to use the full input 36bits of BRAM, we need to pack three sequential pixels together and then write them to the BRAM. However pixels_per_channel will never cleanly divide by three,
# so to avoid edge case handling we only use 24 bits of the BRAM, giving 4 as the required amount of BRAMs for 16 channels.
# With these design constraints fixed the concrete implementation is straight forward.
# 1. On every channel, two sequential pixels are packed into 24bit words. (which are therefore produced every fourth clock cycle).
# 2. Write the words to BRAM. There a four times as many channels as there are BRAMs. And a word is produced every four clock cycles.
#    To be able to read all pixels we need sequentially in a single output cycle, we write sequential words to different BRAMs.
#    Concretely this produces a pattern like this (for `n_channels = 8`)
# The sensor output is sturctured into bursts of 128 pixels, so we need to pay attention to the burst boundaries, as after a burst some overhead cycles take place
# channel written:
# | clock -> | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
# |   bram ∨ |   |   |   |   |   |   |   |   |
# |----------+---+---+---+---+---+---+---+---|
# |        0 | 0 | 2 | 4 | 6 | 1 | 3 | 5 | 6 |
# |        1 | 1 | 3 | 5 | 7 | 0 | 2 | 4 | 7 |
# the addresses written are chosen to just simplify the read out sequence:
# address:
# | clock -> |  1 |   2 |   3 |   4 |  5 |   6 |   7 |   8 |
# |   bram ∨ |    |     |     |     |    |     |     |     |
# |----------+----+-----+-----+-----+----+-----+-----+-----+
# |        0 |  0 | 128 | 256 | 384 | 64 | 172 | 320 | 448 |
# |        1 | 64 | 172 | 320 | 448 |  0 | 128 | 256 | 384 |
#
# on the read out side, we finally can just read the words sequentially out of the BRAMs
# reading:
# | clock -> | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
# |   bram ∨ |   |   |   |   |   |   |   |   |
# |----------+---+---+---+---+---+---+---+---|
# |        0 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
# |        1 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
# a final reordering has to take place, as the first BRAM written to rotates through wrt to the channel
# output order (the number in the table gives the BRAM the word was read from)
# |  clock -> | 1 | 64 | 128 | 172 | 256 |
# | channel ∨ |   |    |     |     |     |
# |-----------+---+----+-----+-----+-----|
# |         0 | 0 |  1 |   0 |   1 |   0 |
# |         1 | 0 |  1 |   0 |   1 |   0 |
# |         2 | 1 |  0 |   1 |   0 |   1 |
# |         3 | 1 |  0 |   1 |   0 |   1 |
#
# TODO(robin): can we avoid that barrel shifter somehow?, Maybe a pipelined shifter?
#
# Now lets finally talk about thae handling of top and bottom side. We know that the bottom side transmits the row immediately after the row of the row transmitted by the top side.
# So if we order the channels to be in the [top_channel, bottom_channel] order, we can just treat this as one row of twice the width (8196) and everything still works.
#
# Finally, all thats left is some scheduling logic, that start the readout process once enough data has be written to the BRAMs.
# n_bram * 2 pixels are read each clock cycle.
# And a single channel gets 1 pixel per clock cycle, for a total of 4096 / n_channel pixels. For example for 8 channels (per side): 512 pixels.
# This means we read out all of the 512 pixels in 32 cycles, so we can start the read out process with 32 pixels left.
# The next row will start soon after the first, so we store two rows and ping pong the buffers
# TODO(robin): this is fucked because of OH, no?
class Cmv12kPixelRemapper(Elaboratable):
    def __init__(self, input: ImageStream, n_bits=12, two_sided_readout=True):
        assert two_sided_readout == True, "single sided readout is not supported"
        assert n_bits == 12, "bit depth other than 12 is not supported"

        self.n_bits = n_bits
        self.input = input

        self.n_channels = len(input.payload) // self.n_bits

        self.output = ImageStream(self.n_bits * self.n_channels // 2)

        self.input_channels = [
            input.payload[n_bits * i : n_bits * (i + 1)] for i in range(self.n_channels)
        ]

        self.output_channels = [
            self.output.payload[n_bits * i : n_bits * (i + 1)] for i in range(self.n_channels // 2)
        ]

        self.row_width = (
            4096 * 2
        )  # we act as if we just have a single row of twice the length of a single row to accomodate the two-sided readout

        self.pixels_per_row_per_channel = self.row_width // self.n_channels

        # fixed sensor parameter
        self.burst_size = 128
        self.bursts_per_channel = self.pixels_per_row_per_channel // self.burst_size

        self.n_mem = self.n_channels // 4

        # each channel writes channel_block_size = row_width / 2 / self.n_mem / self.n_channel words into each BRAM. So we give each a continuous region of that in each BRAM
        # ordered by the channels, so we can just read all BRAMs from the same address for readout
        self.channel_block_size = self.row_width // 2 // self.n_mem // self.n_channels

        # be able to store two full rows
        self.buffer_depth = self.channel_block_size * self.n_channels
        self.mem_depth = self.buffer_depth * 2
        print("pixel_remapper: mem_depth:", self.mem_depth)
        self.addr_width = bits_for(self.mem_depth - 1)

        self.output_words_per_row = self.row_width // self.n_channels

    def elaborate(self, _):
        m = Module()

        # all memories have the same value for these
        rd_enable = Signal()
        rd_address = Signal(self.addr_width)
        wr_enable = Signal()

        # write address, write data and rea data is independent for each memory.
        wr_address = [Signal(self.addr_width, name=f"wr_address_{i:02}") for i in range(self.n_mem)]
        rd_data = [Signal(self.n_bits * 2, name=f"rd_data_{i:02}") for i in range(self.n_mem)]
        wr_data = [Signal(self.n_bits * 2, name=f"wr_data_{i:02}") for i in range(self.n_mem)]

        for idx in range(self.n_mem):
            m.submodules[f"mem_{idx:02}"] = mem = Memory(
                width=2 * self.n_bits, depth=self.mem_depth
            )

            m.submodules[f"mem_{idx:02}_rd"] = rd_port = mem.read_port()
            m.d.comb += rd_port.addr.eq(rd_address)
            m.d.comb += rd_data[idx].eq(rd_port.data)
            m.d.comb += rd_port.en.eq(rd_enable)

            m.submodules[f"mem_{idx:02}_wr"] = wr_port = mem.write_port()
            m.d.comb += wr_port.addr.eq(wr_address[idx])
            m.d.comb += wr_port.data.eq(wr_data[idx])
            m.d.comb += wr_port.en.eq(wr_enable)

        # we double buffer the rows as we cannot wait for all of the data to be read out before we write new data
        buffer_index = Signal()

        # for the further steps we will need a counter to determine when we need to write which fourth
        # we need to count a whole burst and then one extra word, because we can only start
        # writing on the second cycle. This is always possible as bursts are seperated by atleast one OH word
        row_clocks_for_burst = (self.burst_size + 1) * 2
        row_clock_counter = Signal(range(row_clocks_for_burst))
        burst_counter = Signal(range(self.bursts_per_channel))
        with m.If(self.input.valid | row_clock_counter > 0):
            m.d.sync += row_clock_counter.eq(row_clock_counter + 1)

            with m.If(row_clock_counter == (row_clocks_for_burst - 1)):
                m.d.sync += row_clock_counter.eq(0)
                m.d.sync += burst_counter.eq(burst_counter + 1)

                with m.If(burst_counter == (self.bursts_per_channel - 1)):
                    m.d.sync += burst_counter.eq(0)
                    m.d.sync += buffer_index.eq(buffer_index + 1)

        # we need to remember when one of the row pairs were the last rows of a frame to
        # regenerate the frame_last signal on the output_side
        is_frame_last = Array(
            [Signal(name="is_frame_last_buf_0"), Signal(name="is_frame_last_buf_1")]
        )
        with m.If(self.input.valid & (row_clock_counter == 2 * (self.burst_size - 1))):
            with m.If(burst_counter == (self.bursts_per_channel - 1)):
                m.d.sync += is_frame_last[buffer_index].eq(self.input.frame_last)

        # first step: double up the input words. We want to do this with as few FFs as possible. So
        # we use the knowledge that we write the first fourth of channel immediately and only need to store a single pixel
        # for the middle fourths we need to store two pixels, as we need to wait atleast one cycle more
        # for the last forth we need to store three pixels, as a new one comes in before we can write the ol pixel data
        # clock      | 0 | 1 | 2 | 3 | 4 | 5 |
        # data valid | 1 | 0 | 1 | 0 | 1 | 0 |
        # writing    | 0 | 0 | 1 | 1 | 1 | 1 |
        doubled_up_first_fourth = [
            Signal.like(wr_data[0], name=f"doubled_up_first_fourth_{i:02}")
            for i in range(self.n_channels // 4)
        ]
        single_word_registers = [
            Signal.like(self.input_channels[0], name=f"single_word_reg_{i:02}")
            for i in range(len(doubled_up_first_fourth))
        ]
        for doubled, reg, channel in zip(
            doubled_up_first_fourth, single_word_registers, self.input_channels
        ):
            with m.If(self.input.valid):
                m.d.sync += reg.eq(channel)
            m.d.comb += doubled.eq(Cat(channel, reg))

        doubled_up_middle = [
            Signal.like(wr_data[0], name=f"doubled_up_middle_{i:02}")
            for i in range(self.n_channels // 2)
        ]
        double_word_registers = [
            Signal.like(wr_data[0], name=f"double_word_reg_{i:02}")
            for i in range(len(doubled_up_middle))
        ]
        for doubled, reg, channel in zip(
            doubled_up_middle, double_word_registers, self.input_channels[self.n_channels // 4 :]
        ):
            with m.If(self.input.valid):
                m.d.sync += reg.eq((reg << self.n_bits) | channel)
            m.d.comb += doubled.eq(reg)

        doubled_up_last = [
            Signal.like(wr_data[0], name=f"doubled_up_last_{i:02}")
            for i in range(self.n_channels // 4)
        ]
        triple_word_registers = [
            Signal(self.n_bits * 3, name=f"triple_word_reg_{i:02}")
            for i in range(len(doubled_up_last))
        ]
        for doubled, reg, channel in zip(
            doubled_up_last, triple_word_registers, self.input_channels[-self.n_channels // 4 :]
        ):
            # we need to shift these through even if we are in the overhead period.
            # Otherwise for the last word of a burst the pixels we read for doubled will not line up with the actual pixel data
            with m.If((row_clock_counter % 2) == 0):
                m.d.sync += reg.eq((reg << self.n_bits) | channel)
            m.d.comb += doubled.eq(reg[self.n_bits :])

        doubled = Array(doubled_up_first_fourth + doubled_up_middle + doubled_up_last)

        # second step: assign the words to the BRAMs
        # first the data part:
        channel_phase = Signal(range(4))
        word_counter = Signal(range(self.channel_block_size * self.n_mem))

        # NOTE(robin): this assumes self.n_mem will always be a power of two as it relies on the addition overflow behaviour
        shuffle_phase = word_counter[: bits_for(self.n_mem - 1)]
        with m.If(row_clock_counter > 1):
            m.d.comb += wr_enable.eq(1)
            m.d.sync += channel_phase.eq(channel_phase + 1)
            with m.If(channel_phase == 3):
                m.d.sync += word_counter.eq(word_counter + 1)

            for idx, (data, addr) in enumerate(zip(wr_data, wr_address)):
                channel_for_this_mem = self.n_mem * channel_phase + (
                    (idx - shuffle_phase) % self.n_mem
                )
                m.d.comb += data.eq(doubled[channel_for_this_mem])
                # first part: double buffering
                # second part: selecting right block for this channel
                # third part: we strip across all the memories first, then use the next address of our block
                m.d.comb += addr.eq(
                    self.buffer_depth * buffer_index
                    + channel_for_this_mem * self.channel_block_size
                    + word_counter // self.n_mem
                )

        # now the readout part.
        readout_gate = Signal()
        # two rows per buffer
        row_counter = Signal(range(2))

        # uses that self.output_words_per_row is always power of two
        last_output_word_of_row = self.output_words_per_row - 1
        output_word_counter = rd_address[: bits_for(last_output_word_of_row)]

        # we could optimize this a bit further as mention in the long comment above, but this seems a bit useless in the grand scheme of things
        with m.If(Changed(m, buffer_index)):
            m.d.sync += readout_gate.eq(1)
        with m.Elif((row_counter == 1) & (output_word_counter == last_output_word_of_row)):
            m.d.sync += readout_gate.eq(0)

        # address generation is easy:
        with m.If(readout_gate):
            m.d.comb += rd_enable.eq(1)
            # here we use that the buffers are consecutive in memory
            m.d.sync += rd_address.eq(rd_address + 1)

        # address, en -> data has a 1 cycle delay for memories, so we need to delay the output logic by one
        output_gate = Signal()
        rd_address_delayed = Signal.like(rd_address)
        output_word_counter_delayed = rd_address_delayed[: bits_for(last_output_word_of_row)]
        m.d.sync += rd_address_delayed.eq(rd_address)
        m.d.sync += output_gate.eq(readout_gate)

        channel_number = rd_address_delayed[bits_for(self.channel_block_size - 1) :]

        # for debugging
        m.d.comb += Signal(16, name="channel_number").eq(channel_number)

        # now the shuffling
        rd_data_array = Array(rd_data)
        with m.If(output_gate):
            m.d.comb += self.output.valid.eq(1)
            output_channels = self.output_channels
            for i in range(len(self.output_channels) // 2):
                selected = (i + channel_number) % self.n_mem
                # unpack 2 * self.n_bits to two self.n_bits
                m.d.comb += output_channels[2 * i].eq(rd_data_array[selected][self.n_bits :])
                m.d.comb += output_channels[2 * i + 1].eq(rd_data_array[selected][: self.n_bits])

        # finally control channel wrangling
        # two buffers, msb of read address is the buffer we are currently using
        output_buffer_index = rd_address_delayed[-1]
        with m.If(output_gate):
            line_last = output_word_counter_delayed == last_output_word_of_row
            m.d.comb += self.output.line_last.eq(line_last)
            frame_last = is_frame_last[output_buffer_index]
            # we always process rows in pairs, only the second row can be the last one
            m.d.comb += self.output.frame_last.eq(frame_last & line_last & row_counter)
            m.d.sync += row_counter.eq(row_counter + self.output.line_last)

        return m
