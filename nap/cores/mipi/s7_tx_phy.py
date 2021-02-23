from nmigen import *
from nap import BasicStream, ControlSignal
from nap.vendor.xilinx_s7 import DDRSerializer

__all__ = ["MipiMultiLaneTxPhy"]


class MipiMultiLaneTxPhy(Elaboratable):
    def __init__(self, input: BasicStream, clock_pin, lane_pins, ddr_domain):
        self.input = input
        self.clock_pin = clock_pin
        self.lane_pins = lane_pins
        self.ddr_domain = ddr_domain
        self.clock_pattern = ControlSignal(8, reset=0b00001111)

        assert len(input.payload) == len(lane_pins) * 8

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.input.ready.eq(1)
        m.submodules.clock_tx = DDRSerializer(self.clock_pattern, self.clock_pin, self.ddr_domain, bit_width=8, msb_first=False)
        for i, lane_pin in enumerate(self.lane_pins):
            m.submodules[f'lane{i}_phy'] = DDRSerializer(self.input.payload[i * 8: (i + 1) * 8], lane_pin, self.ddr_domain, bit_width=8, msb_first=False)

        return m
