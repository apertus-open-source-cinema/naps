from nmigen import *
from naps import StatusSignal, ControlSignal
from naps.cores import StreamCombiner, StreamInfo, InflexibleSourceDebug, ImageStream
from naps.util import delay_by, ends_with
from .s7_phy import HispiPhy

__all__ = ["HispiRx"]


# those are only the starts of the patterns; they are expanded to the length of the word
control_words = {
    "START_OF_ACTIVE_FRAME_IMAGE_DATA": "00011",
    "START_OF_ACTIVE_FRAME_EMBEDDED_DATA": "10011",
    "START_OF_ACTIVE_LINE_IMAGE_DATA": "00001",
    "START_OF_ACTIVE_LINE_EMBEDDED_DATA": "10001",
    "END_OF_ACTIVE_FRAME": "111",
    "END_OF_ACTIVE_LINE": "101",
    "START_OF_VERTICAL_BLANKING_LINE": "1001",
}


class LaneManager(Elaboratable):
    def __init__(self, input_data: Signal, sync_pattern=(-1, 0, 0)):
        """
        Aligns the word boundries of one Hispi lane and detects control codes.
        Compatible only with Packetized-SP mode because it needs end markers.

        :param sync_pattern: the preamble of a control word (default is correct for most cases)
        :param timeout: Issue a bit slip after a control word wasnt found for n cycles
        """
        self.sync_pattern = sync_pattern
        self.input_data = input_data

        self.is_aligned = StatusSignal()

        self.timeout = ControlSignal(32, reset=10000)
        self.timeouts_to_resync = ControlSignal(32, reset=10000)

        self.since_last_sync_pattern_or_bitslip = StatusSignal(32)
        self.performed_bitslips = StatusSignal(32)
        self.timeouts_since_alignment = StatusSignal(32)
        self.last_word = StatusSignal(input_data.shape())
        self.last_control_word = StatusSignal(
            input_data.shape(),
            decoder=lambda x: next((
                "{}/{:012b}".format(control_word, x)
                for control_word, ending
                in control_words.items()
                if "{:012b}".format(x).endswith(ending)
            ), "UNKNOWN/{:012b}".format(x))
        )

        self.do_bitslip = Signal()
        self.output = ImageStream(self.input_data.shape())

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.last_word.eq(self.input_data)
        m.d.comb += self.output.payload.eq(self.input_data)

        with m.If(self.since_last_sync_pattern_or_bitslip < self.timeout):
            m.d.sync += self.since_last_sync_pattern_or_bitslip.eq(self.since_last_sync_pattern_or_bitslip + 1)
        with m.Else():
            with m.If(self.is_aligned):
                with m.If(self.timeouts_since_alignment > self.timeouts_to_resync):
                    m.d.sync += self.is_aligned.eq(0)
                    m.d.sync += self.timeouts_since_alignment.eq(0)
                with m.Else():
                    m.d.sync += self.timeouts_since_alignment.eq(self.timeouts_since_alignment + 1)
            with m.Else():
                m.d.sync += self.since_last_sync_pattern_or_bitslip.eq(0)
                m.d.sync += self.performed_bitslips.eq(self.performed_bitslips + 1)
                m.d.comb += self.do_bitslip.eq(1)

        with m.FSM():
            for i, pattern_word in enumerate(self.sync_pattern):
                with m.State("sync{}".format(i)):
                    with m.If(self.input_data == Const(pattern_word, self.input_data.shape())):
                        if i < len(self.sync_pattern) - 1:
                            m.next = "sync{}".format(i + 1)
                        else:
                            m.next = "control_word"
                    with m.Else():
                        with m.If(self.input_data == Const(self.sync_pattern[0], self.input_data.shape())):
                            m.next = "sync1"
                        with m.Else():
                            m.next = "sync0"
            with m.State("control_word"):
                with m.If(ends_with(self.input_data, *control_words.values())):
                    m.d.sync += self.last_control_word.eq(self.input_data)
                    m.d.sync += self.since_last_sync_pattern_or_bitslip.eq(0)
                    m.d.sync += self.is_aligned.eq(1)
                m.next = "sync0"

        # assemble the output stream
        valid = Signal()
        m.d.comb += valid.eq(ends_with(
            self.last_control_word,
            # control_words["START_OF_ACTIVE_FRAME_EMBEDDED_DATA"],
            control_words["START_OF_ACTIVE_FRAME_IMAGE_DATA"],
            # control_words["START_OF_ACTIVE_LINE_EMBEDDED_DATA"],
            control_words["START_OF_ACTIVE_LINE_IMAGE_DATA"]
        ))

        # delay is needed because we only know that the line finished when the control code is done
        # this is len(sync_pattern) + 1 + 1 cycles after the line really ended
        delayed_valid = delay_by(valid, len(self.sync_pattern) + 2, m)
        delayed_data = delay_by(self.input_data, len(self.sync_pattern) + 2, m)

        with m.If(ends_with(self.last_control_word,
                            control_words["END_OF_ACTIVE_FRAME"], control_words["END_OF_ACTIVE_LINE"])):
            m.d.sync += delayed_valid.eq(0)

        m.d.comb += self.output.payload.eq(delayed_data)
        m.d.comb += self.output.valid.eq(delayed_valid)
        m.d.comb += self.output.frame_last.eq(ends_with(self.last_control_word, control_words["END_OF_ACTIVE_FRAME"]))
        m.d.comb += self.output.line_last.eq(ends_with(self.last_control_word, control_words["END_OF_ACTIVE_LINE"], control_words["END_OF_ACTIVE_FRAME"]))

        m.submodules.debug = InflexibleSourceDebug(self.output)

        return m


class HispiRx(Elaboratable):
    def __init__(self, sensor, bits=12, hispi_domain="hispi"):
        self.hispi_domain = hispi_domain
        self.lvds_clk = sensor.lvds_clk
        self.lvds = sensor.lvds
        self.lanes = len(self.lvds)
        self.bits = bits

        self.output = ImageStream(len(self.lvds) * bits)
        self.output_domain = hispi_domain
        self.phy = HispiPhy(num_lanes=self.lanes, bits=self.bits, hispi_domain=hispi_domain)

    def elaborate(self, platform):
        m = Module()

        phy = m.submodules.phy = self.phy
        m.d.comb += phy.hispi_clk.eq(self.lvds_clk)
        m.d.comb += phy.hispi_lanes.eq(self.lvds)

        in_hispi_domain = DomainRenamer(self.hispi_domain)

        streams = []
        for i, lane in enumerate(phy.out):
            lane_manager = m.submodules["lane_manager_{}".format(i)] = in_hispi_domain(LaneManager(lane))

            m.d.comb += phy.bitslip[i].eq(lane_manager.do_bitslip)

            m.d.comb += self.output.payload[i * self.bits: (i + 1) * self.bits].eq(lane_manager.input_data)
            streams.append(lane_manager.output)

        stream_combiner = m.submodules.stream_combiner = in_hispi_domain(StreamCombiner(*streams, merge_payload=True))
        m.submodules.output_stream_info = in_hispi_domain(StreamInfo(stream_combiner.output))
        m.d.comb += self.output.connect_upstream(stream_combiner.output)

        return m
