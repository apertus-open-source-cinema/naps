from contextlib import contextmanager
from nmigen import *
from naps import StatusSignal, PacketizedStream, TristateIo, StreamBuffer

# control mode lp symbols
from naps.util.past import Rose

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

    def __init__(self, lp_pins: TristateIo, hs_pins: TristateIo, ddr_domain, initial_driving=True):
        self.lp_pins = lp_pins
        self.hs_pins = hs_pins
        self.ddr_domain = ddr_domain

        # The control rx and control tx signals carry the raw escape mode packets.
        # After each transmitted packet, a bus turnaround is requested.
        # This should lead to either the result in case of a read request or an ack trigger for MIPI DSI
        self.control_input = PacketizedStream(8)
        self.control_output = PacketizedStream(8)

        self.is_lp = StatusSignal(reset=True)
        self.is_driving = StatusSignal(reset=initial_driving)

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.lp_pins.oe.eq(self.is_lp & self.is_driving)
        m.d.comb += self.hs_pins.oe.eq(~self.is_lp & self.is_driving)

        @contextmanager
        def delay(cycles):
            timer = Signal(range(cycles))
            is_delay = Signal()
            m.d.comb += is_delay.eq(1)
            try:
                with m.If(timer < cycles):
                    m.d.sync += timer.eq(timer + 1)
                with m.If(Rose(m, is_delay)):
                    m.d.sync += timer.eq(0)
                else_stmt = m.Else()
                else_stmt.__enter__()
                yield None
            finally:
                else_stmt.__exit__(None, None, None)

        def delay_next(cycles, next_state):
            with delay(cycles):
                m.next = next_state

        with m.If(self.is_driving):
            lp = self.lp_pins.o
            with m.FSM(name="tx_fsm"):
                with m.State("IDLE"):
                    m.d.comb += lp.eq(STOP)
                    with m.If(self.control_input.valid):
                        m.next = "LP_REQUEST"
                with m.State("LP_REQUEST"):
                    m.d.comb += lp.eq(LP_REQUEST)
                    delay_next(1, "LP_REQUEST_BRIDGE")
                with m.State("LP_REQUEST_BRIDGE"):
                    m.d.comb += lp.eq(BRIDGE)
                    delay_next(1, "ESCAPE_REQUEST")
                with m.State("ESCAPE_REQUEST"):
                    m.d.comb += lp.eq(ESCAPE_REQUEST)
                    delay_next(1, "ESCAPE_REQUEST_BRIDGE")
                with m.State("ESCAPE_REQUEST_BRIDGE"):
                    m.d.comb += lp.eq(BRIDGE)
                    delay_next(1, "ESCAPE_0")

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
                                with delay(1):
                                    m.next = "ESCAPE_FINISH"
                                    m.d.comb += self.control_input.ready.eq(1)
                            with m.Else():
                                with delay(1):
                                    m.next = "ESCAPE_0"
                                    m.d.comb += self.control_input.ready.eq(1)

                with m.State("ESCAPE_FINISH"):
                    m.d.comb += lp.eq(MARK_1)
                    delay_next(1, "ESCAPE_FINISH_STOP")
                with m.State("ESCAPE_FINISH_STOP"):
                    m.d.comb += lp.eq(STOP)
                    delay_next(10, "TURNAROUND_LP_REQUEST")  # TODO: reduce the delay; it is here to ease debugging :)

                with m.State("TURNAROUND_LP_REQUEST"):
                    m.d.comb += lp.eq(LP_REQUEST)
                    delay_next(1, "TURNAROUND_LP_REQUEST_BRIDGE")
                with m.State("TURNAROUND_LP_REQUEST_BRIDGE"):
                    m.d.comb += lp.eq(BRIDGE)
                    delay_next(1, "TURNAROUND_REQUEST")
                with m.State("TURNAROUND_REQUEST"):
                    m.d.comb += lp.eq(TURNAROUND_REQUEST)
                    delay_next(1, "TURNAROUND_REQUEST_BRIDGE")
                with m.State("TURNAROUND_REQUEST_BRIDGE"):
                    m.d.comb += lp.eq(BRIDGE)
                    with delay(4):
                        m.next = "IDLE"
                        m.d.sync += self.is_driving.eq(0)  # this makes us leave this FSM and enter the one below
                    # TODO: implement BTA timeout


        # we buffer the control output to be able to meet the stream contract
        control_output_unbuffered = PacketizedStream(8)
        control_output_buffer = m.submodules.control_output_buffer = StreamBuffer(control_output_unbuffered)
        m.d.comb += self.control_output.connect_upstream(control_output_buffer.output)

        with m.If(~self.is_driving):
            lp = self.lp_pins.i
            with m.FSM(name="rx_fsm"):
                def maybe_next(condition, next_state):
                    with m.If(condition):
                        m.next = next_state

                def maybe_stop():
                    maybe_next(lp == STOP, "STOP")

                with m.State("STOP"):
                    maybe_next(lp == LP_REQUEST, "AFTER-LP-REQUEST")
                    maybe_stop()

                with m.State("AFTER-LP-REQUEST"):
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
                        with delay(4):
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
