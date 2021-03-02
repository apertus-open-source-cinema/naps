# remaps the cmv12k output lanes into an ImageStream with subsequent pixels
# the raw lane output of the cmv12k is a bit wired

from typing import List

from nmigen import *
from naps import BasicStream, packed_struct
from naps.cores import ImageStream, BufferedSyncStreamFIFO

__all__ = ["Cmv12kPixelRemapper"]

@packed_struct
class ControlChannelWord:
    data_valid: unsigned(1)
    line_valid: unsigned(1)
    frame_valid: unsigned(1)
    fot: unsigned(1)
    integration_1: unsigned(1)
    integration_2: unsigned(1)


class Cmv12kPixelRemapper(Elaboratable):
    """Remaps one output port (if top and bottom outputs of the cmv12k are used, instantiate this twice!) to provide a linear output.

    Generally the CMV12000 sends its data out in bursts.
    The output format of the CMV12000 (and therefore the input for this core) depends on two factors:
    the number of lanes used and the presence of subsampling  / binning. The burst length is described by
    line_length / n_lanes_per_side so for the non line_lengh of 4096 and 16 lanes per side
    (the default beta configuration) this equals to a burst_length of 256.
    One Lane always sends adjacent pixels of bust_length out.

    """
    def __init__(self, top_lanes: List[Signal], bottom_lanes: List[Signal], control_lane: Signal):
        self.lanes = top_lanes
        self.bottom_lanes = bottom_lanes
        self.control_lane = control_lane
        assert len(top_lanes) == len(bottom_lanes)

        self.lines_to_buffer = 64 // (len(top_lanes) + len(bottom_lanes))
        self.n_bits = len(top_lanes[0])
        self.n_lanes_per_side = len(top_lanes)

        self.output = ImageStream(self.n_bits)

    def elaborate(self, platform):
        m = Module()

        cw = ControlChannelWord(self.control_lane)

        lane_top_streams_buffered = []
        for i, signal in enumerate(self.top_lanes):
            stream = BasicStream(self.n_bits)
            m.d.comb += stream.payload.eq(signal)
            m.d.comb += stream.valid.eq(cw.data_valid)

            fifo = m.submodules[f"fifo_top{i}"] = BufferedSyncStreamFIFO(stream, depth=128 * (self.lines_to_buffer + 1))
            lane_top_streams_buffered.append(fifo.output)

        return m
