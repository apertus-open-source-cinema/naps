from nmigen import *

from cores.csr_bank import StatusSignal
from cores.hispi.hispi_phy import HispiPhy


class ControlSequenceDecoder(Elaboratable):
    def __init__(self, input_data: Signal, pattern=(0b111111111111, 0b000000000000, 0b000000000000), timeout=2000):
        self.pattern = pattern
        self.timeout = timeout

        self.data = input_data
        self.data_valid = StatusSignal()
        self.last_word = StatusSignal(input_data.shape())
        self.last_control_word = StatusSignal(input_data.shape())
        self.cycles_since_last_pattern = StatusSignal(range(timeout))
        self.do_bitslip = StatusSignal()
        self.performed_bitslips = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.last_word.eq(self.data)

        with m.If(self.cycles_since_last_pattern < self.timeout):
            m.d.sync += self.cycles_since_last_pattern.eq(self.cycles_since_last_pattern + 1)
        with m.Else():
            m.d.sync += self.cycles_since_last_pattern.eq(0)
            m.d.sync += self.data_valid.eq(0)
            m.d.comb += self.do_bitslip.eq(1)
            m.d.sync += self.performed_bitslips.eq(self.performed_bitslips + 1)

        with m.FSM():
            for i, pattern_byte in enumerate(self.pattern):
                with m.State(str(i)):
                    with m.If(self.data == pattern_byte):
                        m.next = str(i + 1)
                    with m.Else():
                        m.next = "0"
            with m.State(str(len(self.pattern))):
                m.next = "0"
                m.d.sync += self.last_control_word.eq(self.data)
                m.d.sync += self.cycles_since_last_pattern.eq(0)
                m.d.sync += self.data_valid.eq(1)

        return m


class Hispi(Elaboratable):
    def __init__(self, sensor):
        self.lvds_clk = sensor.lvds_clk
        self.lvds = sensor.lvds

    def elaborate(self, platform):
        m = Module()

        num_lanes = 4

        phy = m.submodules.phy = HispiPhy(num_lanes=num_lanes)
        m.d.comb += phy.hispi_clk.eq(self.lvds_clk)
        m.d.comb += phy.hispi_lanes.eq(self.lvds)

        for i, lane in enumerate(phy.out):
            lane_decoder = m.submodules["control_sequence_decoder_{}".format(i)] = DomainRenamer("hispi")(
                ControlSequenceDecoder(lane))
            m.d.comb += phy.bitslip[i].eq(lane_decoder.do_bitslip)

        return m
