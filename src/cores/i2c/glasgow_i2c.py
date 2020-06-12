# I2C reference: https://www.nxp.com/docs/en/user-guide/UM10204.pdf

from nmigen.compat import *
from nmigen.compat.genlib.cdc import MultiReg


__all__ = ["I2CInitiator", "I2CTarget"]


class I2CBus(Module):
    """
    I2C bus.
    Decodes bus conditions (start, stop, sample and setup) and provides synchronization.
    """
    def __init__(self, pads):
        self.scl_t = pads.scl_t if hasattr(pads, "scl_t") else pads.scl
        self.sda_t = pads.sda_t if hasattr(pads, "sda_t") else pads.sda

        self.scl_i = Signal()
        self.scl_o = Signal(reset=1)
        self.sda_i = Signal()
        self.sda_o = Signal(reset=1)

        self.sample = Signal(name="bus_sample")
        self.setup  = Signal(name="bus_setup")
        self.start  = Signal(name="bus_start")
        self.stop   = Signal(name="bus_stop")

        ###

        scl_r = Signal(reset=1)
        sda_r = Signal(reset=1)

        self.comb += [
            self.scl_t.o.eq(0),
            self.scl_t.oe.eq(~self.scl_o),
            self.sda_t.o.eq(0),
            self.sda_t.oe.eq(~self.sda_o),

            self.sample.eq(~scl_r & self.scl_i),
            self.setup.eq(scl_r & ~self.scl_i),
            self.start.eq(self.scl_i & sda_r & ~self.sda_i),
            self.stop.eq(self.scl_i & ~sda_r & self.sda_i),
        ]
        self.sync += [
            scl_r.eq(self.scl_i),
            sda_r.eq(self.sda_i),
        ]
        self.specials += [
            MultiReg(self.scl_t.i, self.scl_i, reset=1),
            MultiReg(self.sda_t.i, self.sda_i, reset=1),
        ]


class I2CInitiator(Module):
    """
    Simple I2C transaction initiator.
    Generates start and stop conditions, and transmits and receives octets.
    Clock stretching is supported.
    :param period_cyc:
        Bus clock period, as a multiple of system clock period.
    :type period_cyc: int
    :param clk_stretch:
        If true, SCL will be monitored for devices stretching the clock. Otherwise,
        only interally generated SCL is considered.
    :type clk_stretch: bool
    :attr busy:
        Busy flag. Low if the state machine is idle, high otherwise.
    :attr start:
        Start strobe. When ``busy`` is low, asserting ``start`` for one cycle generates
        a start or repeated start condition on the bus. Ignored when ``busy`` is high.
    :attr stop:
        Stop strobe. When ``busy`` is low, asserting ``stop`` for one cycle generates
        a stop condition on the bus. Ignored when ``busy`` is high.
    :attr write:
        Write strobe. When ``busy`` is low, asserting ``write`` for one cycle receives
        an octet on the bus and latches it to ``data_o``, after which the acknowledge bit
        is asserted if ``ack_i`` is high. Ignored when ``busy`` is high.
    :attr data_i:
        Data octet to be transmitted. Latched immediately after ``write`` is asserted.
    :attr ack_o:
        Received acknowledge bit.
    :attr read:
        Read strobe. When ``busy`` is low, asserting ``read`` for one cycle latches
        ``data_i`` and transmits it on the bus, after which the acknowledge bit
        from the bus is latched to ``ack_o``. Ignored when ``busy`` is high.
    :attr data_o:
        Received data octet.
    :attr ack_i:
        Acknowledge bit to be transmitted. Latched immediately after ``read`` is asserted.
    """
    def __init__(self, pads, period_cyc, clk_stretch=True):
        self.busy   = Signal(reset=1)
        self.start  = Signal()
        self.stop   = Signal()
        self.read   = Signal()
        self.data_i = Signal(8)
        self.ack_o  = Signal()
        self.write  = Signal()
        self.data_o = Signal(8)
        self.ack_i  = Signal()

        self.submodules.bus = bus = I2CBus(pads)

        ###

        period_cyc = int(period_cyc)

        timer = Signal(max=period_cyc)
        stb   = Signal()

        self.sync += [
            If((timer == 0) | ~self.busy,
                timer.eq(period_cyc // 4)
            ).Elif((not clk_stretch) | (bus.scl_o == bus.scl_i),
                timer.eq(timer - 1)
            )
        ]
        self.comb += stb.eq(timer == 0)

        bitno   = Signal(max=8)
        r_shreg = Signal(8)
        w_shreg = Signal(8)
        r_ack   = Signal()

        self.submodules.fsm = FSM(reset_state="IDLE")

        def scl_l(state, next_state, *exprs):
            self.fsm.act(state,
                If(stb,
                   NextValue(bus.scl_o, 0),
                   NextState(next_state),
                   *exprs
                )
            )
        def scl_h(state, next_state, *exprs):
            self.fsm.act(state,
                If(stb,
                    NextValue(bus.scl_o, 1)
                ).Elif(bus.scl_o == 1,
                    If((not clk_stretch) | (bus.scl_i == 1),
                        NextState(next_state),
                        *exprs
                    )
                )
            )
        def stb_x(state, next_state, *exprs):
            self.fsm.act(state,
                If(stb,
                    NextState(next_state),
                    *exprs
                )
            )

        self.fsm.act("IDLE",
            NextValue(self.busy, 1),
            If(self.start,
                If(bus.scl_i & bus.sda_i,
                    NextState("START-SDA-L")
                ).Elif(~bus.scl_i,
                    NextState("START-SCL-H")
                ).Elif(bus.scl_i,
                    NextState("START-SCL-L")
                )
            ).Elif(self.stop,
                If(bus.scl_i & ~bus.sda_o,
                    NextState("STOP-SDA-H")
                ).Elif(~bus.scl_i,
                    NextState("STOP-SCL-H")
                ).Elif(bus.scl_i,
                    NextState("STOP-SCL-L")
                )
            ).Elif(self.write,
                NextValue(w_shreg, self.data_i),
                NextState("WRITE-DATA-SCL-L")
            ).Elif(self.read,
                NextValue(r_ack, self.ack_i),
                NextState("READ-DATA-SCL-L")
            ).Else(
                NextValue(self.busy, 0)
            )
        )
        # start
        scl_l("START-SCL-L", "START-SDA-H")
        stb_x("START-SDA-H", "START-SCL-H",
            NextValue(bus.sda_o, 1)
        )
        scl_h("START-SCL-H", "START-SDA-L")
        stb_x("START-SDA-L", "IDLE",
            NextValue(bus.sda_o, 0)
        )
        # stop
        scl_l("STOP-SCL-L",  "STOP-SDA-L")
        stb_x("STOP-SDA-L",  "STOP-SCL-H",
            NextValue(bus.sda_o, 0)
        )
        scl_h("STOP-SCL-H",  "STOP-SDA-H")
        stb_x("STOP-SDA-H",  "IDLE",
            NextValue(bus.sda_o, 1)
        )
        # write data
        scl_l("WRITE-DATA-SCL-L", "WRITE-DATA-SDA-X")
        stb_x("WRITE-DATA-SDA-X", "WRITE-DATA-SCL-H",
            NextValue(bus.sda_o, w_shreg[7])
        )
        scl_h("WRITE-DATA-SCL-H", "WRITE-DATA-SDA-N",
            NextValue(w_shreg, Cat(C(0, 1), w_shreg[0:7]))
        )
        stb_x("WRITE-DATA-SDA-N", "WRITE-DATA-SCL-L",
            NextValue(bitno, bitno + 1),
            If(bitno == 7,
                NextState("WRITE-ACK-SCL-L")
            )
        )
        # write ack
        scl_l("WRITE-ACK-SCL-L", "WRITE-ACK-SDA-H")
        stb_x("WRITE-ACK-SDA-H", "WRITE-ACK-SCL-H",
            NextValue(bus.sda_o, 1)
        )
        scl_h("WRITE-ACK-SCL-H", "WRITE-ACK-SDA-N",
            NextValue(self.ack_o, ~bus.sda_i)
        )
        stb_x("WRITE-ACK-SDA-N", "IDLE")
        # read data
        scl_l("READ-DATA-SCL-L", "READ-DATA-SDA-H")
        stb_x("READ-DATA-SDA-H", "READ-DATA-SCL-H",
            NextValue(bus.sda_o, 1)
        )
        scl_h("READ-DATA-SCL-H", "READ-DATA-SDA-N",
            NextValue(r_shreg, Cat(bus.sda_i, r_shreg[0:7]))
        )
        stb_x("READ-DATA-SDA-N", "READ-DATA-SCL-L",
            NextValue(bitno, bitno + 1),
            If(bitno == 7,
                NextState("READ-ACK-SCL-L")
            )
        )
        # read ack
        scl_l("READ-ACK-SCL-L", "READ-ACK-SDA-X")
        stb_x("READ-ACK-SDA-X", "READ-ACK-SCL-H",
            NextValue(bus.sda_o, ~r_ack),
        )
        scl_h("READ-ACK-SCL-H", "READ-ACK-SDA-N",
            NextValue(self.data_o, r_shreg)
        )
        stb_x("READ-ACK-SDA-N", "IDLE")


class I2CTarget(Module):
    """
    Simple I2C target.
    Clock stretching is not supported.
    Builtin responses (identification, general call, etc.) are not provided.
    Note that the start, stop, and restart strobes are transaction delimiters rather than direct
    indicators of bus conditions. A transaction always starts with a start strobe and ends with
    either a stop or a restart strobe. That is, a restart strobe, similarly to a stop strobe, may
    be only followed by another start strobe (or no strobe at all if the device is not addressed
    again).
    :attr address:
        The 7-bit address the target will respond to.
    :attr start:
        Start strobe. Active for one cycle immediately after acknowledging address.
    :attr stop:
        Stop stobe. Active for one cycle immediately after a stop condition that terminates
        a transaction that addressed this device.
    :attr restart:
        Repeated start strobe. Active for one cycle immediately after a repeated start condition
        that terminates a transaction that addressed this device.
    :attr write:
        Write strobe. Active for one cycle immediately after receiving a data octet.
    :attr data_i:
        Data octet received from the initiator. Valid when ``write`` is high.
    :attr ack_o:
        Acknowledge strobe. If active for at least one cycle during the acknowledge bit
        setup period (one half-period after write strobe is asserted), acknowledge is asserted.
        Otherwise, no acknowledge is asserted. May use combinatorial feedback from ``write``.
    :attr read:
        Read strobe. Active for one cycle immediately before latching ``data_o``.
    :attr data_o:
        Data octet to be transmitted to the initiator. Latched immedately after receiving
        a read command.
    """
    def __init__(self, pads):
        self.address = Signal(7)
        self.busy    = Signal() # clock stretching request (experimental, undocumented)
        self.start   = Signal()
        self.stop    = Signal()
        self.restart = Signal()
        self.write   = Signal()
        self.data_i  = Signal(8)
        self.ack_o   = Signal()
        self.read    = Signal()
        self.data_o  = Signal(8)
        self.ack_i   = Signal()

        self.submodules.axi = bus = I2CBus(pads)

        ###

        bitno   = Signal(max=8)
        shreg_i = Signal(8)
        shreg_o = Signal(8)

        self.submodules.fsm = FSM(reset_state="IDLE")
        self.fsm.act("IDLE",
            If(bus.start,
                NextState("START"),
            )
        )
        self.fsm.act("START",
            If(bus.stop,
                # According to the spec, technically illegal, "but many devices handle
                # this anyway". Can Philips, like, decide on whether they want it or not??
                NextState("IDLE")
            ).Elif(bus.setup,
                NextValue(bitno, 0),
                NextState("ADDR-SHIFT")
            )
        )
        self.fsm.act("ADDR-SHIFT",
            If(bus.stop,
                NextState("IDLE")
            ).Elif(bus.start,
                NextState("START")
            ).Elif(bus.sample,
                NextValue(shreg_i, (shreg_i << 1) | bus.sda_i),
            ).Elif(bus.setup,
                NextValue(bitno, bitno + 1),
                If(bitno == 7,
                    If(shreg_i[1:] == self.address,
                        self.start.eq(1),
                        NextValue(bus.sda_o, 0),
                        NextState("ADDR-ACK")
                    ).Else(
                        NextState("IDLE")
                    )
                )
            )
        )
        self.fsm.act("ADDR-ACK",
            If(bus.stop,
                self.stop.eq(1),
                NextState("IDLE")
            ).Elif(bus.start,
                self.restart.eq(1),
                NextState("START")
            ).Elif(bus.setup,
                If(~shreg_i[0],
                    NextValue(bus.sda_o, 1),
                    NextState("WRITE-SHIFT")
                )
            ).Elif(bus.sample,
                If(shreg_i[0],
                    NextValue(shreg_o, self.data_o),
                    NextState("READ-STRETCH")
                )
            )
        )
        self.fsm.act("WRITE-SHIFT",
            If(bus.stop,
                self.stop.eq(1),
                NextState("IDLE")
            ).Elif(bus.start,
                self.restart.eq(1),
                NextState("START")
            ).Elif(bus.sample,
                NextValue(shreg_i, (shreg_i << 1) | bus.sda_i),
            ).Elif(bus.setup,
                NextValue(bitno, bitno + 1),
                If(bitno == 7,
                    NextValue(self.data_i, shreg_i),
                    NextState("WRITE-ACK")
                )
            )
        )
        self.comb += self.write.eq(self.fsm.after_entering("WRITE-ACK"))
        self.fsm.act("WRITE-ACK",
            If(bus.stop,
                self.stop.eq(1),
                NextState("IDLE")
            ).Elif(bus.start,
                self.restart.eq(1),
                NextState("START")
            ).Elif(bus.setup,
                NextValue(bus.sda_o, 1),
                NextState("WRITE-SHIFT")
            ).Elif(~bus.scl_i,
                NextValue(bus.scl_o, ~self.busy),
                If(self.ack_o,
                    NextValue(bus.sda_o, 0)
                )
            )
        )
        self.comb += self.read.eq(self.fsm.before_entering("READ-STRETCH"))
        self.fsm.act("READ-STRETCH",
            If(self.busy,
                NextValue(shreg_o, self.data_o)
            ),
            If(bus.stop,
                self.stop.eq(1),
                NextState("IDLE")
            ).Elif(bus.start,
                NextState("START")
            ).Elif(self.busy,
                If(~bus.scl_i,
                    NextValue(bus.scl_o, 0)
                )
            ).Else(
                If(~bus.scl_i,
                    NextValue(bus.sda_o, shreg_o[7])
                ),
                NextValue(bus.scl_o, 1),
                NextState("READ-SHIFT")
            )
        )
        self.fsm.act("READ-SHIFT",
            If(bus.stop,
                self.stop.eq(1),
                NextState("IDLE")
            ).Elif(bus.start,
                self.restart.eq(1),
                NextState("START")
            ).Elif(bus.setup,
                NextValue(bus.sda_o, shreg_o[7]),
            ).Elif(bus.sample,
                NextValue(shreg_o, shreg_o << 1),
                NextValue(bitno, bitno + 1),
                If(bitno == 7,
                    NextState("READ-ACK")
                )
            )
        )
        self.fsm.act("READ-ACK",
            If(bus.stop,
                self.stop.eq(1),
                NextState("IDLE")
            ).Elif(bus.start,
                self.restart.eq(1),
                NextState("START")
            ).Elif(bus.setup,
                NextValue(bus.sda_o, 1),
            ).Elif(bus.sample,
                If(~bus.sda_i,
                    NextValue(shreg_o, self.data_o),
                    NextState("READ-STRETCH")
                ).Else(
                    self.stop.eq(1),
                    NextState("IDLE")
                )
            )
        )

class _DummyPads(Module):
    def __init__(self):
        self.scl_t = TSTriple()
        self.sda_t = TSTriple()