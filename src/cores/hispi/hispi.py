from nmigen import *

from cores.csr_bank import StatusSignal
from cores.hispi.s7_phy import HispiPhy
from cores.stream.combiner import StreamCombiner
from cores.stream.stream import StreamEndpoint

# those are only the starts of the patterns; they are expanded to the length of the byte
from util.nmigen import delay_by, ends_with

START_OF_ACTIVE_FRAME_IMAGE_DATA = "11000"
START_OF_ACTIVE_FRAME_EMBEDDED_DATA = "11001"
START_OF_ACTIVE_LINE_IMAGE_DATA = "10000"
START_OF_ACTIVE_LINE_EMBEDDED_DATA = "10001"
END_OF_ACTIVE_FRAME = "111"
END_OF_ACTIVE_LINE = "101"
START_OF_VERTICAL_BLANKING_LINE = "1001"


class LaneManager(Elaboratable):
    def __init__(self, input_data: Signal, sync_pattern=(-1, 0, 0), timeout=2000):
        """
        Aligns the word boundries of one Hispi lane and detects control codes.
        Compatible only with Packetized-SP mode because it needs end markers.

        :param sync_pattern: the preamble of a control word (default is correct for most cases)
        :param timeout: Issue a bit slip after a control word wasnt found for n cycles
        """
        self.sync_pattern = sync_pattern
        self.timeout = timeout
        self.input_data = input_data

        self.is_aligned = StatusSignal()

        self.last_control_word = StatusSignal(input_data.shape())
        self.cycles_since_last_sync_pattern = StatusSignal(range(timeout))
        self.performed_bitslips = StatusSignal(32)
        self.last_word = StatusSignal(input_data.shape())

        self.do_bitslip = Signal()
        self.output = StreamEndpoint(Signal.like(self.input_data), is_sink=False, has_last=True)

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.last_word.eq(self.input_data)

        with m.If(self.cycles_since_last_sync_pattern < self.timeout):
            m.d.sync += self.cycles_since_last_sync_pattern.eq(self.cycles_since_last_sync_pattern + 1)
        with m.Else():
            m.d.sync += self.cycles_since_last_sync_pattern.eq(0)
            m.d.sync += self.is_aligned.eq(0)
            m.d.comb += self.do_bitslip.eq(1)
            m.d.sync += self.performed_bitslips.eq(self.performed_bitslips + 1)

        with m.FSM():
            for i, pattern_byte in enumerate(self.sync_pattern):
                with m.State(str(i)):
                    with m.If(self.input_data == Const(pattern_byte, self.input_data.shape())):
                        m.next = str(i + 1)
                    with m.Else():
                        m.next = "0"
            with m.State(str(len(self.sync_pattern))):
                m.next = "0"
                m.d.sync += self.last_control_word.eq(self.input_data)
                m.d.sync += self.cycles_since_last_sync_pattern.eq(0)
                m.d.sync += self.is_aligned.eq(1)

        # assemble the output stream
        valid = Signal()
        m.d.comb += valid.eq(ends_with(
            self.last_control_word,
            START_OF_ACTIVE_FRAME_EMBEDDED_DATA,
            START_OF_ACTIVE_FRAME_IMAGE_DATA,
            START_OF_ACTIVE_LINE_EMBEDDED_DATA,
            START_OF_ACTIVE_LINE_IMAGE_DATA
        ))

        # delay is needed because we only know that the line finished when the control code is done
        # this is len(sync_pattern) + 1 + 1 cycles after the line really ended
        delayed_valid = delay_by(valid, len(self.sync_pattern) + 2, m)
        delayed_data = delay_by(self.input_data, len(self.sync_pattern) + 2, m)

        with m.If(ends_with(self.last_control_word, END_OF_ACTIVE_FRAME, END_OF_ACTIVE_LINE)):
            m.d.sync += delayed_valid.eq(0)

        with m.If(ends_with(self.last_control_word, END_OF_ACTIVE_FRAME)):
            m.d.comb += self.output.last.eq(1)

        m.d.comb += self.output.payload.eq(delayed_data)
        m.d.comb += self.output.valid.eq(delayed_valid)
        m.d.comb += self.output.last.eq(ends_with(self.last_control_word, END_OF_ACTIVE_FRAME))

        return m


class Hispi(Elaboratable):
    def __init__(self, sensor, bits=12):
        self.lvds_clk = sensor.lvds_clk
        self.lvds = sensor.lvds
        self.lanes = len(self.lvds)
        self.bits = bits

        self.output = StreamEndpoint(Signal(len(self.lvds) * bits), is_sink=False, has_last=True)

    def elaborate(self, platform):
        m = Module()

        phy = m.submodules.phy = HispiPhy(num_lanes=self.lanes, bits=self.bits)
        m.d.comb += phy.hispi_clk.eq(self.lvds_clk)
        m.d.comb += phy.hispi_lanes.eq(self.lvds)

        streams = []
        for i, lane in enumerate(phy.out):
            lane_manager = m.submodules["lane_manager_{}".format(i)] = DomainRenamer("hispi")(LaneManager(lane))
            m.d.comb += phy.bitslip[i].eq(lane_manager.do_bitslip)
            m.d.comb += self.output.payload[i * self.bits: (i + 1) * self.bits].eq(lane_manager.input_data)
            streams.append(lane_manager.output)

        stream_combiner = m.submodules.stream_combiner = DomainRenamer("hispi")(StreamCombiner(streams))
        m.d.comb += self.output.connect(stream_combiner.output, allow_back_to_back=True)

        return m
