from contextlib import contextmanager
from nmigen import *
from nmigen.lib.cdc import FFSynchronizer

from naps import StatusSignal, PacketizedStream, TristateIo, StreamBuffer, trigger, probe, process_delay, process_block, Process, TristateDdrIo, BasicStream, process_write_to_stream, BufferedAsyncStreamFIFO
from naps.cores.debug.ila import fsm_probe
from naps.util.nmigen_misc import bit_reversed
from naps.util.past import NewHere


# control mode lp symbols
STOP = 0b11
HS_REQUEST = 0b01
LP_REQUEST = 0b10
TURNAROUND_REQUEST = 0b10
ESCAPE_REQUEST = 0b01
BRIDGE = 0b00

# escape mode lp symbols
SPACE = 0b00
MARK_0 = 0b01
MARK_1 = 0b10


def fake_differential(v):
    return Mux(v, 0b01, 0b10)


class MipiDPhyDataLane(Elaboratable):
    """ A mipi D-Phy Data lane that can handle bidirectional lp data transfer and unidirectional hs transfer.

    The `sync` domain of this module should run at 2x the LP Hold period. Eg if the hold period is 66ns, the sync domain should run at 30 Mhz
    (these are reasonable values btw). This is needed to be able to sample the incoming data during bus turnaround since there is no fixed phase relation (nyquist).
    """

    def __init__(self, lp_pins: TristateIo, hs_pins: TristateDdrIo, initial_driving=True, is_lane_0=False, ddr_domain="sync"):
        self.lp_pins = lp_pins
        self.hs_pins = hs_pins
        self.is_lane_0 = is_lane_0
        self.ddr_domain = ddr_domain

        # The control rx and control tx signals carry the raw escape mode packets.
        # After each transmitted packet, a bus turnaround is requested.
        # This should lead to either the result in case of a read request or an ack trigger for MIPI DSI
        self.control_input = PacketizedStream(8)
        self.control_output = PacketizedStream(8)

        # the hs_input stream carries is polled to
        self.hs_input = PacketizedStream(8)

        self.is_hs = StatusSignal()
        self.is_driving = StatusSignal(reset=initial_driving)
        self.bta_timeout = 1023
        self.bta_timeouts = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.lp_pins.oe.eq(self.is_driving)
        m.d.comb += self.hs_pins.oe.eq(self.is_hs & self.is_driving)

        def delay_lp(cycles):
            return process_delay(m, cycles * 6)

        def delay_next(cycles, next_state):
            with delay_lp(cycles):
                m.next = next_state

        m.d.comb += self.hs_pins.o_clk.eq(ClockSignal(self.ddr_domain))

        hs_idle = Signal()
        hs_words = BasicStream(8)
        hs_fifo = m.submodules.hs_fifo = BufferedAsyncStreamFIFO(hs_words, 8, o_domain=self.ddr_domain)
        with m.FSM(name="serializer_fsm", domain=self.ddr_domain) as fsm:
            if self.is_lane_0:
                fsm_probe(m, fsm)
            hs_payload = Signal(8)
            m.d.comb += hs_payload.eq(Mux(hs_fifo.output.valid, hs_fifo.output.payload, Repl(hs_idle, 8)))
            for i in range(4):
                with m.State(f"{i}"):
                    if i == 3:
                        m.d.comb += hs_fifo.output.ready.eq(1)
                    m.d.comb += self.hs_pins.o0.eq(fake_differential(hs_payload[i * 2 + 0]))
                    m.d.comb += self.hs_pins.o1.eq(fake_differential(hs_payload[i * 2 + 1]))
                    m.next = f"{(i + 1) % 4}"

        @process_block
        def send_hs(data):
            return process_write_to_stream(m, hs_words, data)

        if self.is_lane_0:
            trig = Signal()

            trigger(m, trig)
            probe(m, self.lp_pins.oe)
            probe(m, self.lp_pins.o)
            probe(m, self.lp_pins.i)
            probe(m, self.hs_pins.oe)
            probe(m, hs_payload)
        else:
            trig = Signal()

        bta_timeout_counter = Signal(range(self.bta_timeout))
        bta_timeout_possible = Signal()

        with m.If(self.is_driving):
            lp = bit_reversed(self.lp_pins.o)
            with m.FSM(name="tx_fsm") as fsm:
                if self.is_lane_0:
                    fsm_probe(m, fsm)
                with m.State("IDLE"):
                    m.d.comb += lp.eq(STOP)
                    with delay_lp(1):
                        with m.If(self.control_input.valid):
                            m.next = "LP_REQUEST"
                        with m.Elif(self.hs_input.valid):
                            m.next = "HS_REQUEST"

                with m.State("HS_REQUEST"):
                    m.d.comb += trig.eq(1)
                    with Process(m, name="hs_request") as p:
                        m.d.sync += hs_idle.eq(0)
                        m.d.comb += lp.eq(HS_REQUEST)
                        p += delay_lp(1)
                        m.d.comb += lp.eq(BRIDGE)
                        p += delay_lp(3)
                        m.d.sync += self.is_hs.eq(1)
                        p += delay_lp(4)  # we are in HS-ZERO now and wait the constant part (150ns)
                        p += send_hs(Repl(0, 8))
                        p += send_hs(Repl(0, 8))
                        p += send_hs(Const(0b10111000, 8))
                        m.next = "HS_SEND"

                with m.State("HS_SEND"):
                    with send_hs(self.hs_input.payload):
                        with m.If(self.hs_input.last):
                            m.next = "HS_END"
                        with m.Else():
                            m.next = "HS_SEND"
                            m.d.comb += self.hs_input.ready.eq(1)

                with m.State("HS_END"):
                    with Process(m, name="hs_end") as p:
                        m.d.sync += hs_idle.eq(~self.hs_input.payload[7])
                        p += send_hs(Repl(~self.hs_input.payload[7], 8))
                        p += send_hs(Repl(~self.hs_input.payload[7], 8))
                        p += send_hs(Repl(~self.hs_input.payload[7], 8))
                        with m.If(NewHere(m)):
                            m.d.comb += self.hs_input.ready.eq(1)
                        p += m.If(hs_fifo.w_level == 0)
                        m.d.sync += self.is_hs.eq(0)
                        m.d.comb += lp.eq(STOP)
                        p += delay_lp(10)
                        m.d.comb += lp.eq(STOP)
                        if self.is_lane_0:
                            m.next = "TURNAROUND_LP_REQUEST"
                        else:
                            m.next = "IDLE"

                with m.State("LP_REQUEST"):
                    with Process(m, name="lp_request") as p:
                        m.d.comb += lp.eq(LP_REQUEST)
                        p += delay_lp(1)
                        m.d.comb += lp.eq(BRIDGE)
                        p += delay_lp(1)
                        m.d.comb += lp.eq(ESCAPE_REQUEST)
                        p += delay_lp(1)
                        m.d.comb += lp.eq(BRIDGE)
                        p += delay_lp(1)
                        m.next = "ESCAPE_0"

                for bit in range(8):
                    with m.State(f"ESCAPE_{bit}"):
                        with m.If(self.control_input.valid):  # after transmitting the first byte, this can be false. the mipi spec allows us to wait here (in space state)
                            with m.If(self.control_input.payload[bit]):
                                m.d.comb += lp.eq(MARK_1)
                            with m.Else():
                                m.d.comb += lp.eq(MARK_0)
                            delay_next(1, f"ESCAPE_{bit}_SPACE")
                    with m.State(f"ESCAPE_{bit}_SPACE"):
                        m.d.comb += lp.eq(SPACE)
                        if bit < 7:
                            delay_next(1, f"ESCAPE_{bit + 1}")
                        else:
                            with m.If(self.control_input.last):  # according to the stream contract, this may not change, until we assert ready :)
                                with delay_lp(1):
                                    m.next = "ESCAPE_FINISH"
                                    m.d.comb += self.control_input.ready.eq(1)
                            with m.Else():
                                with delay_lp(1):
                                    m.next = "ESCAPE_0"
                                    m.d.comb += self.control_input.ready.eq(1)

                with m.State("ESCAPE_FINISH"):
                    with Process(m) as p:
                        m.d.comb += lp.eq(MARK_1)
                        p += delay_lp(1)
                        m.d.comb += lp.eq(STOP)
                        p += delay_lp(10)  # TODO: reduce the delay; it is here to ease debugging :)
                        m.next = "TURNAROUND_LP_REQUEST"

                with m.State("TURNAROUND_LP_REQUEST"):
                    with Process(m, name="turnaround_lp_request") as p:
                        m.d.comb += lp.eq(LP_REQUEST)
                        p += delay_lp(1)
                        m.d.comb += lp.eq(BRIDGE)
                        p += delay_lp(1)
                        m.d.comb += lp.eq(TURNAROUND_REQUEST)
                        p += delay_lp(1)
                        m.d.comb += lp.eq(BRIDGE)
                        p += delay_lp(4)
                        m.next = "IDLE"
                        m.d.sync += self.is_driving.eq(0)  # this makes us leave this FSM and enter the one below
                        m.d.sync += bta_timeout_counter.eq(0)
                        m.d.sync += bta_timeout_possible.eq(1)

        # we buffer the control output to be able to meet the stream contract
        control_output_unbuffered = PacketizedStream(8)
        control_output_buffer = m.submodules.control_output_buffer = StreamBuffer(control_output_unbuffered)
        m.d.comb += self.control_output.connect_upstream(control_output_buffer.output)

        with m.If(~self.is_driving):
            lp = Signal(2)
            m.submodules += FFSynchronizer(bit_reversed(self.lp_pins.i), lp)

            with m.FSM(name="rx_fsm") as fsm:
                if self.is_lane_0:
                    fsm_probe(m, fsm)

                def maybe_next(condition, next_state):
                    with m.If(condition):
                        m.next = next_state

                def maybe_stop():
                    maybe_next(lp == STOP, "STOP")

                with m.State("STOP"):
                    with m.If(bta_timeout_possible):
                        with m.If(bta_timeout_counter < self.bta_timeout):
                            m.d.sync += bta_timeout_counter.eq(bta_timeout_counter + 1)
                        with m.Else():
                            m.d.sync += self.bta_timeouts.eq(self.bta_timeouts + 1)
                            m.d.sync += self.is_driving.eq(1)
                            m.d.sync += bta_timeout_counter.eq(0)
                            m.d.sync += bta_timeout_possible.eq(0)
                    maybe_next(lp == LP_REQUEST, "AFTER-LP-REQUEST")
                    maybe_stop()

                with m.State("AFTER-LP-REQUEST"):
                    m.d.sync += bta_timeout_possible.eq(0)
                    with m.If(lp == BRIDGE):
                        m.next = "AFTER-LP-REQUEST-BRIDGE"
                    maybe_stop()
                with m.State("AFTER-LP-REQUEST-BRIDGE"):
                    with m.If(lp == ESCAPE_REQUEST):
                        m.next = "AFTER-ESCAPE-REQUEST"
                    with m.Elif(lp == TURNAROUND_REQUEST):
                        m.next = "AFTER-TURNAROUND-REQUEST"
                    maybe_stop()

                with m.State("AFTER-TURNAROUND-REQUEST"):
                    with m.If(lp == BRIDGE):
                        with delay_lp(4):
                            m.next = "STOP"
                            m.d.sync += self.is_driving.eq(1)
                    maybe_stop()

                with m.State("AFTER-ESCAPE-REQUEST"):
                    with m.If(lp == BRIDGE):
                        m.next = "ESCAPE_0"

                # we keep track if we have already sent the currently or last received bit over our output stream.
                # we send it either on the first bit of the next word or during the stop condition
                outboxed = Signal(reset=1)

                def maybe_finish_escape():
                    with m.If(lp == STOP):
                        m.next = "STOP"
                        m.d.sync += outboxed.eq(1)
                        with m.If(~outboxed):
                            m.d.comb += control_output_unbuffered.last.eq(1)
                            m.d.comb += control_output_unbuffered.valid.eq(1)

                bit_value = Signal()
                for bit in range(8):
                    with m.State(f"ESCAPE_{bit}"):
                        with m.If(lp == MARK_0):
                            m.d.sync += bit_value.eq(0)
                            m.next = f"ESCAPE_{bit}_SPACE"
                        with m.If(lp == MARK_1):
                            m.d.sync += bit_value.eq(1)
                            m.next = f"ESCAPE_{bit}_SPACE"
                        maybe_finish_escape()
                    with m.State(f"ESCAPE_{bit}_SPACE"):
                        with m.If(lp == SPACE):
                            if bit == 0:
                                with m.If(~outboxed):
                                    m.d.comb += control_output_unbuffered.valid.eq(1)
                                    m.d.sync += outboxed.eq(1)

                            m.d.sync += control_output_unbuffered.payload[bit].eq(bit_value)
                            m.d.sync += outboxed.eq(0)
                            m.next = f"ESCAPE_{(bit + 1) % 8}"
                        maybe_finish_escape()

        return m


class MipiDPhyClockLane(Elaboratable):
    def __init__(self, lp_pins: TristateIo, hs_pins: TristateDdrIo, ddr_domain="sync"):
        self.lp_pins = lp_pins
        self.hs_pins = hs_pins
        self.ddr_domain = ddr_domain

        self.request_hs = Signal()
        self.is_hs = StatusSignal()

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.lp_pins.oe.eq(1)
        m.d.comb += self.hs_pins.oe.eq(self.is_hs)
        m.d.comb += self.hs_pins.o_clk.eq(ClockSignal(self.ddr_domain))
        lp = bit_reversed(self.lp_pins.o)

        io = platform.request("io", 0)
        m.d.comb += io.oe.eq(1)
        trig = io.o[13]
        m.d.comb += trig.eq(self.request_hs)

        with m.If(~self.is_hs):
            m.d.comb += lp.eq(STOP)
            with m.If(self.request_hs):
                with Process(m, name="hs_request") as p:
                    p += process_delay(m, 6)  # we need to stay in lp state for some minimum time
                    m.d.comb += lp.eq(HS_REQUEST)
                    p += process_delay(m, 6)
                    m.d.comb += lp.eq(BRIDGE)
                    p += process_delay(m, 5)
                    m.d.sync += self.is_hs.eq(1)
        with m.Else():
            with m.If(~self.request_hs):
                with Process(m, name="hs_end") as p:
                    m.d.comb += self.hs_pins.o0.eq(fake_differential(0))
                    m.d.comb += self.hs_pins.o1.eq(fake_differential(0))
                    p += process_delay(m, 2)  # delay minimum 60ns
                    m.d.sync += self.is_hs.eq(1)
            with m.Else():
                m.d.comb += self.hs_pins.o0.eq(fake_differential(0))
                m.d.comb += self.hs_pins.o1.eq(fake_differential(1))

        return m
