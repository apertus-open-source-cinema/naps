from nmigen import *

from cores.blink_debug import BlinkDebug
from cores.jtag.jtag import JTAG


class JTAGPeripheralConnector(Elaboratable):
    def __init__(self, peripheral):
        """
        A simple `PeripheralConnector` implementation for querying `Peripheral`s via JTAG in debug situations.
        This code does not handle memorymap stuff. Use in combination with PeripheralsAggregator
        """

        assert callable(peripheral.handle_read) and callable(peripheral.handle_write)
        assert isinstance(peripheral.range, range)
        self.peripheral = peripheral

    def elaborate(self, platform):
        m = Module()
        jtag = m.submodules.jtag = JTAG()
        m.submodules.in_jtag_domain = DomainRenamer("jtag")(self.elaborate_jtag_domain(platform, jtag))
        return m

    def elaborate_jtag_domain(self, platform, jtag):
        m = Module()
        state = Signal(4)

        write = Signal()
        addr = Signal(32)
        data = Signal(32)
        status = Signal()

        m.d.comb += platform.jtag_signals.eq(Cat(ClockSignal("jtag"), jtag.tdi, jtag.tdo, jtag.shift_read, jtag.shift_write, jtag.reset, state, write))

        read_write_done = Signal()

        def read_write_done_callback(error):
            m.d.sync += status.eq(error)
            m.d.sync += read_write_done.eq(1)

        # jtag_fsm is a seperate domain so that when the jtag fsm is reset all the csrs keep their value
        # (they are also implicitly part of the jtag domain because they are driven from it)
        m.domains += ClockDomain("jtag_fsm")
        m.d.comb += ClockSignal("jtag_fsm").eq(ClockSignal())
        m.d.comb += ResetSignal("jtag_fsm").eq(jtag.reset)
        with m.FSM(domain="jtag_fsm"):
            def next_on_jtag_shift(next_state, is_tdi):
                with m.If(jtag.shift_read if is_tdi else jtag.shift_write):
                    m.next = next_state

            with m.State("CMD"):  # we recive one bit that indicates if we want to read (0) or write (1)
                m.d.comb += state.eq(0)
                m.d.sync += write.eq(jtag.tdi)
                next_on_jtag_shift("ADDR0", is_tdi=True)

            # address states
            for i in range(32):
                with m.State("ADDR{}".format(i)):
                    m.d.comb += state.eq(1)
                    m.d.sync += addr[i].eq(jtag.tdi)
                    if i < 31:
                        next_on_jtag_shift("ADDR{}".format(i + 1), is_tdi=True)
                    else:
                        with m.If(write):
                            next_on_jtag_shift("WRITE0", is_tdi=True)
                        with m.Else():
                            next_on_jtag_shift("READ_WAIT", is_tdi=True)

            # read states
            with m.State("READ_WAIT"):
                m.d.comb += state.eq(2)
                self.peripheral.handle_read(m, addr, data, read_write_done_callback)
                with m.If(read_write_done):
                    m.d.comb += jtag.tdo.eq(1)
                    next_on_jtag_shift("READ0", is_tdi=False)
            for i in range(32):
                with m.State("READ{}".format(i)):
                    m.d.comb += state.eq(3)
                    m.d.comb += jtag.tdo.eq(data[i])
                    if i < 31:
                        next_on_jtag_shift("READ{}".format(i + 1), is_tdi=False)
                    else:
                        next_on_jtag_shift("READ_STATUS", is_tdi=False)
            with m.State("READ_STATUS"):
                m.d.comb += state.eq(6)
                m.d.comb += jtag.tdo.eq(status)
                next_on_jtag_shift("CMD", is_tdi=False)

            # write states
            for i in range(32):
                with m.State("WRITE{}".format(i)):
                    m.d.comb += state.eq(4)
                    m.d.sync += data[i].eq(jtag.tdi)
                    if i < 31:
                        next_on_jtag_shift("WRITE{}".format(i + 1), is_tdi=True)
                    else:
                        next_on_jtag_shift("WRITE_WAIT", is_tdi=True)
            with m.State("WRITE_WAIT"):
                m.d.comb += state.eq(5)
                self.peripheral.handle_write(m, addr, data, read_write_done_callback)
                with m.If(read_write_done):
                    m.d.comb += jtag.tdo.eq(1)
                    next_on_jtag_shift("WRITE_STATUS", is_tdi=True)
            with m.State("WRITE_STATUS"):
                m.d.comb += state.eq(6)
                m.d.comb += jtag.tdo.eq(status)
                next_on_jtag_shift("CMD", is_tdi=False)

        return m
