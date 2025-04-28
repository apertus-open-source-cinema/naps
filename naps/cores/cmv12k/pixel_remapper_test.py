#!/usr/bin/env python3

import pytest
from naps import SimPlatform, ImageStream
from naps.cores.cmv12k.pixel_remapper import Cmv12kPixelRemapper


# these are the combinations supported currently
@pytest.mark.parametrize("channels_per_side", [4, 8, 16, 32])
def test_cmv12k_pixel_remapper(channels_per_side):
    platform = SimPlatform()
    # fixed for now
    # TODO(robin): support more
    n_bits = 12

    input_stream = ImageStream(2 * channels_per_side * n_bits)
    dut = Cmv12kPixelRemapper(input_stream, n_bits=n_bits, two_sided_readout=True)

    # we ping pong buffers of two rows, so check that atleast buffer 0, 1, 0 works
    num_rows_per_side = 5

    full_width = 4096
    pixels_per_channel = full_width // channels_per_side

    # this is fixed, after a burst there always is atleast a single cycle of overhead OH
    burst_size = 128

    n_bursts = num_rows_per_side * pixels_per_channel // burst_size
    burst_per_row = pixels_per_channel // burst_size

    frame_last_after_set = [0, 1, 4]

    def generate_row_data():
        frame_idx = 0
        for burst in range(n_bursts):
            row_set = burst // burst_per_row
            burst = burst % burst_per_row
            for p in range(burst_size):
                pixel = burst * burst_size + p

                # one word every second cycle
                yield input_stream.valid.eq(0)
                yield

                yield input_stream.valid.eq(1)
                line_last = p + 1 == burst_size
                yield input_stream.line_last.eq(line_last)
                frame_last = (
                    line_last
                    and (row_set == frame_last_after_set[frame_idx])
                    and burst == (burst_per_row - 1)
                )
                yield input_stream.frame_last.eq(frame_last)
                if frame_last:
                    frame_idx += 1
                for channel in range(channels_per_side):
                    yield input_stream.payload[n_bits * channel : n_bits * (channel + 1)].eq(
                        pixels_per_channel * channel + pixel + 2 * row_set
                    )
                    yield input_stream.payload[
                        n_bits * (channel + channels_per_side) : n_bits
                        * (channel + channels_per_side + 1)
                    ].eq(pixels_per_channel * channel + pixel + 2 * row_set + 1)

                yield

            yield input_stream.line_last.eq(0)
            yield input_stream.frame_last.eq(0)
            yield input_stream.valid.eq(0)
            # one word overhead every burst
            yield
            yield

    expected_row_data = [
        (i + r) % full_width for r in range(2 * num_rows_per_side) for i in range(full_width)
    ]  # + list(range(full_width)) * (2 * num_rows_per_side)

    def read_row_data():
        debug = False
        row_data = []
        while len(row_data) < len(expected_row_data):
            if (yield dut.output.valid):
                packed_word = yield dut.output.payload
                row_data += [(packed_word >> (12 * i)) & 0xFFF for i in range(channels_per_side)]
                if len(row_data) % full_width == 0:
                    assert (yield dut.output.line_last) == 1
                    row_count = len(row_data) // full_width
                    if row_count % 2 == 0 and (row_count // 2 - 1) in frame_last_after_set:
                        assert (yield dut.output.frame_last) == 1

            yield

        if debug:
            bs = 16
            for block in range(len(row_data) // bs):
                print(
                    "got:  " + " ".join(f"{x: 5}" for x in row_data[block * bs : (block + 1) * bs])
                )
                print(
                    "want: "
                    + " ".join(f"{x: 5}" for x in expected_row_data[block * bs : (block + 1) * bs])
                )

        for _ in range(100):
            yield
        assert expected_row_data == row_data

    platform.add_process(generate_row_data, "sync")
    platform.add_process(read_row_data, "sync")
    platform.add_sim_clock("sync", 100e6)
    platform.sim(dut)


if __name__ == "__main__":
    test_cmv12k_pixel_remapper(16)
