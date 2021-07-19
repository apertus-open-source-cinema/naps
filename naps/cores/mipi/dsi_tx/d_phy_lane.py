from nmigen import *
from nmigen.lib.cdc import FFSynchronizer

from naps import StatusSignal, PacketizedStream, TristateIo, process_delay, process_block, Process, TristateDdrIo, process_write_to_stream, NewHere, fake_differential
from naps.cores import StreamBuffer, Serializer, fsm_status_reg, fsm_probe

__all__ = ["DPhyDataLane", "DPhyClockLane"]


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


class DPhyDataLane(Elaboratable):
    """ A mipi D-Phy Data lane that can handle bidirectional lp data transfer and unidirectional hs transfer.

    The `sync` domain of this module should run at 2x the LP Hold period. Eg if the hold period is 66ns, the sync domain should run at 30 Mhz
    (these are reasonable values btw). This is needed to be able to sample the incoming data during bus turnaround since there is no fixed phase relation (nyquist).
    """

    def __init__(self, lp_pins: TristateIo, hs_pins: TristateDdrIo, initial_driving=True, can_lp=False, ddr_domain="sync"):
        self.lp_pins = lp_pins
        self.hs_pins = hs_pins
        self.can_lp = can_lp
        self.ddr_domain = ddr_domain

        if self.can_lp:
            # The control rx and control tx signals carry the raw escape mode packets.
            # A packet with length 1 and payload 0x0 indicates that we request a bus turnaround.
            # This in Not a valid MIPI Escape Entry Code so we simply repurpose that here.
            self.control_input = PacketizedStream(8)
            self.control_output = PacketizedStream(8)

        # the hs_input stream carries is polled to
        self.hs_input = PacketizedStream(8)

        self.is_hs = StatusSignal()
        self.is_driving = StatusSignal(reset=initial_driving) if can_lp else True
        self.bta_timeout = 1023
        self.bta_timeouts = StatusSignal(16)

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.lp_pins.oe.eq(self.is_driving)

        def delay_lp(cycles):
            return process_delay(m, cycles * 4)

        serializer_reset = Signal()
        m.d.comb += serializer_reset.eq(~(self.is_hs & self.is_driving))
        serializer = m.submodules.serializer = Serializer(self.hs_pins, width=8, ddr_domain=self.ddr_domain, reset=serializer_reset)

        @process_block
        def send_hs(data):
            return process_write_to_stream(m, serializer.input, payload=data)

        bta_timeout_counter = Signal(range(self.bta_timeout))
        bta_timeout_possible = Signal()

        with m.If(self.is_driving):
            lp = self.lp_pins.o[::-1]
            with m.FSM(name="tx_fsm") as fsm:
                fsm_status_reg(platform, m, fsm)
                with m.State("IDLE"):
                    m.d.comb += lp.eq(STOP)
                    if self.can_lp:
                        with m.If(self.control_input.valid & (self.control_input.payload == 0x00) & self.control_input.last):
                            m.d.comb += self.control_input.ready.eq(1)
                            m.next = "TURNAROUND_LP_REQUEST"
                        with m.Elif(self.control_input.valid):
                            m.next = "LP_REQUEST"
                        with m.Elif(self.hs_input.valid):
                            m.next = "HS_REQUEST"
                    else:
                        with m.If(self.hs_input.valid):
                            m.next = "HS_REQUEST"

                with Process(m, name="HS_REQUEST", to="HS_SEND") as p:
                    m.d.comb += lp.eq(HS_REQUEST)
                    p += delay_lp(1)
                    m.d.comb += lp.eq(BRIDGE)
                    p += delay_lp(3)
                    m.d.sync += self.is_hs.eq(1)
                    p += delay_lp(4)  # we are in HS-ZERO now and wait the constant part (150ns)
                    p += send_hs(Repl(0, 8))
                    p += send_hs(Repl(0, 8))
                    p += send_hs(Const(0b10111000, 8))

                with m.State("HS_SEND"):
                    with send_hs(self.hs_input.payload):
                        with m.If(self.hs_input.last):
                            m.next = "HS_END"
                        with m.Else():
                            m.next = "HS_SEND"
                            m.d.comb += self.hs_input.ready.eq(1)

                with Process(m, name="HS_END", to="IDLE") as p:
                    p += send_hs(Repl(~self.hs_input.payload[7], 8))
                    p += send_hs(Repl(~self.hs_input.payload[7], 8))
                    with m.If(NewHere(m)):
                        m.d.comb += self.hs_input.ready.eq(1)
                    p += m.If(serializer.is_idle)
                    m.d.sync += self.is_hs.eq(0)
                    p += process_delay(m, 1)  # TODO: this is currently tied to the way we do ddr (beaks when we change clock frequencies)
                    m.d.comb += lp.eq(STOP)
                    p += delay_lp(2)

                if self.can_lp:
                    with Process(m, name="LP_REQUEST", to="ESCAPE_0") as p:
                        m.d.comb += lp.eq(LP_REQUEST)
                        p += delay_lp(1)
                        m.d.comb += lp.eq(BRIDGE)
                        p += delay_lp(1)
                        m.d.comb += lp.eq(ESCAPE_REQUEST)
                        p += delay_lp(1)
                        m.d.comb += lp.eq(BRIDGE)
                        p += delay_lp(1)

                    for bit in range(8):
                        with m.State(f"ESCAPE_{bit}"):
                            with m.If(self.control_input.valid):  # after transmitting the first byte, this can be false. the mipi spec allows us to wait here (in space state)
                                with m.If(self.control_input.payload[bit]):
                                    m.d.comb += lp.eq(MARK_1)
                                with m.Else():
                                    m.d.comb += lp.eq(MARK_0)
                                with delay_lp(1):
                                    m.next = f"ESCAPE_{bit}_SPACE"
                        with m.State(f"ESCAPE_{bit}_SPACE"):
                            m.d.comb += lp.eq(SPACE)
                            if bit < 7:
                                with delay_lp(1):
                                    m.next = f"ESCAPE_{bit + 1}"
                            else:
                                with m.If(self.control_input.last):  # according to the stream contract, this may not change, until we assert ready :)
                                    with delay_lp(1):
                                        m.next = "ESCAPE_FINISH"
                                        m.d.comb += self.control_input.ready.eq(1)
                                with m.Else():
                                    with delay_lp(1):
                                        m.next = "ESCAPE_0"
                                        m.d.comb += self.control_input.ready.eq(1)

                    with Process(m, "ESCAPE_FINISH", to="IDLE") as p:
                        m.d.comb += lp.eq(MARK_1)
                        p += delay_lp(1)
                        m.d.comb += lp.eq(STOP)
                        p += delay_lp(10)  # TODO: reduce the delay; it is here to ease debugging :)

                    with Process(m, name="TURNAROUND_LP_REQUEST", to="TURNAROUND_RETURN") as p:
                        m.d.comb += lp.eq(LP_REQUEST)
                        p += delay_lp(1)
                        m.d.comb += lp.eq(BRIDGE)
                        p += delay_lp(1)
                        m.d.comb += lp.eq(TURNAROUND_REQUEST)
                        p += delay_lp(1)
                        m.d.comb += lp.eq(BRIDGE)
                        p += delay_lp(4)
                        m.d.sync += self.is_driving.eq(0)  # this makes us leave this FSM and enter the one below
                        m.d.sync += bta_timeout_counter.eq(0)
                        m.d.sync += bta_timeout_possible.eq(1)
                        p += process_delay(m, 1)

                    with Process(m, name="TURNAROUND_RETURN", to="IDLE") as p:
                        m.d.comb += lp.eq(STOP)
                        p += delay_lp(10)

        if self.can_lp:

            # we buffer the control output to be able to meet the stream contract
            control_output_unbuffered = PacketizedStream(8)
            control_output_buffer = m.submodules.control_output_buffer = StreamBuffer(control_output_unbuffered)
            m.d.comb += self.control_output.connect_upstream(control_output_buffer.output)

            with m.If(~self.is_driving):
                lp = Signal(2)
                m.submodules += FFSynchronizer(self.lp_pins.i[::-1], lp)

                with m.FSM(name="rx_fsm") as fsm:
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


class DPhyClockLane(Elaboratable):
    def __init__(self, lp_pins: TristateIo, hs_pins: TristateDdrIo, ck_domain):
        self.lp_pins = lp_pins
        self.hs_pins = hs_pins
        self.ck_domain = ck_domain

        self.request_hs = Signal()
        self.is_hs = StatusSignal()

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.lp_pins.oe.eq(1)
        m.d.comb += self.hs_pins.oe.eq(self.is_hs)
        m.d.comb += self.hs_pins.o_clk.eq(ClockSignal(self.ck_domain))
        lp = self.lp_pins.o[::-1]

        with m.FSM():
            with m.State("LP"):
                m.d.comb += lp.eq(STOP)
                with m.If(self.request_hs):
                    m.next = "HS_REQUEST"
            with Process(m, "HS_REQUEST", to="HS") as p:
                m.d.comb += lp.eq(STOP)
                p += process_delay(m, 6)  # we need to stay in lp state for some minimum time
                m.d.comb += lp.eq(HS_REQUEST)
                p += process_delay(m, 6)
                m.d.comb += lp.eq(BRIDGE)
                p += process_delay(m, 5)
            with m.State("HS"):
                m.d.comb += lp.eq(0)
                m.d.comb += self.is_hs.eq(1)
                m.d.comb += self.hs_pins.o0.eq(fake_differential(1))
                m.d.comb += self.hs_pins.o1.eq(fake_differential(0))
                with m.If(~self.request_hs):
                    m.next = "HS_END"
            with Process(m, name="HS_END", to="LP") as p:
                m.d.comb += self.is_hs.eq(1)
                m.d.comb += lp.eq(0)
                m.d.comb += self.hs_pins.o0.eq(fake_differential(0))
                m.d.comb += self.hs_pins.o1.eq(fake_differential(0))
                p += process_delay(m, 2)  # delay minimum 60ns

        return m
