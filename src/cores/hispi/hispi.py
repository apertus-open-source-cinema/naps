from nmigen import *

from cores.csr_bank import StatusSignal, ControlSignal
from cores.hispi.s7_phy import HispiPhy
from cores.stream.combiner import StreamCombiner
from soc.pydriver.drivermethod import driver_property
from util.stream import StreamEndpoint

# those are only the starts of the patterns; they are expanded to the length of the word
from util.nmigen_misc import delay_by, ends_with

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
        self.last_control_word = StatusSignal(
            input_data.shape(),
            decoder=lambda x: next((
                "{}/{:012b}".format(control_word, x)
                for control_word, ending
                in control_words.items()
                if "{:012b}".format(x).endswith(ending)
            ), "UNKNOWN/{:012b}".format(x))
        )
        self.last_word = StatusSignal(input_data.shape())

        self.do_bitslip = Signal()
        self.output = StreamEndpoint(self.input_data.shape(), is_sink=False, has_last=True)

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
            control_words["START_OF_ACTIVE_FRAME_EMBEDDED_DATA"],
            control_words["START_OF_ACTIVE_FRAME_IMAGE_DATA"],
            control_words["START_OF_ACTIVE_LINE_EMBEDDED_DATA"],
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
        m.d.comb += self.output.last.eq(ends_with(self.last_control_word, control_words["END_OF_ACTIVE_FRAME"]))

        return m


class Hispi(Elaboratable):
    def __init__(self, sensor, bits=12):
        self.lvds_clk = sensor.lvds_clk
        self.lvds = sensor.lvds
        self.lanes = len(self.lvds)
        self.bits = bits

        self.width = StatusSignal(range(10000))
        self.height = StatusSignal(range(10000))
        self.frame_count = StatusSignal(32)

        self.output = StreamEndpoint(len(self.lvds) * bits, is_sink=False, has_last=True)
        self.phy = HispiPhy(num_lanes=self.lanes, bits=self.bits)

    def elaborate(self, platform):
        m = Module()

        phy = m.submodules.phy = self.phy
        m.d.comb += phy.hispi_clk.eq(self.lvds_clk)
        m.d.comb += phy.hispi_lanes.eq(self.lvds)

        streams = []
        for i, lane in enumerate(phy.out):
            lane_manager = m.submodules["lane_manager_{}".format(i)] = DomainRenamer("hispi")(LaneManager(lane))

            m.d.comb += phy.bitslip[i].eq(lane_manager.do_bitslip)

            m.d.comb += self.output.payload[i * self.bits: (i + 1) * self.bits].eq(lane_manager.input_data)
            streams.append(lane_manager.output)

            if i == 0:
                was_valid = Signal()
                m.d.hispi += was_valid.eq(lane_manager.output.valid)
                with_counter = Signal.like(self.width)
                height_counter = Signal.like(self.height)
                with m.If(lane_manager.output.valid):
                    m.d.hispi += with_counter.eq(with_counter + 1)
                with m.Elif(was_valid):
                    m.d.hispi += self.width.eq(with_counter * self.lanes)
                    m.d.hispi += with_counter.eq(0)
                    m.d.hispi += height_counter.eq(height_counter + 1)
                with m.If(lane_manager.output.last & (height_counter > 10)):
                    m.d.hispi += self.frame_count.eq(self.frame_count + 1)
                    m.d.hispi += self.height.eq(height_counter)
                    m.d.hispi += height_counter.eq(0)

        stream_combiner = m.submodules.stream_combiner = DomainRenamer("hispi")(StreamCombiner(streams))
        m.d.comb += self.output.connect(stream_combiner.output, allow_back_to_back=True)

        return m

    @driver_property
    def fps(self):
        from time import sleep
        start_frames = self.frame_count
        sleep(1)
        return self.frame_count - start_frames