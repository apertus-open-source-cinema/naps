from nmigen import *

from lib.bus.stream.stream import BasicStream


class ZeroRle(Elaboratable):
    """
    Converts a stream of numbers into a stream of numbers (with identity mapping) and numbers for different
    run lengths of zeroes (with a dict of possible run lenghts).
    """
    def __init__(self, input: BasicStream, possible_run_lengths_list, zero_value):
        self.input = input
        self.possible_run_lengths_list = possible_run_lengths_list
        self.zero_value = zero_value

        self.output = BasicStream(range(2**len(self.input.payload) + len(possible_run_lengths_list)))

    def elaborate(self, platform):
        m = Module()

            

        return m
