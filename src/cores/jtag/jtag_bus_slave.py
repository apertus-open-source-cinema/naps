from nmigen import *

from cores.blink_debug import BlinkDebug
from cores.jtag.jtag import JTAG
from util.nmigen_misc import connect_leds


class JTAGBusSlave(Elaboratable):
    def __init__(self, handle_read, handle_write):
        """
        A simple BusSlave implemention for querying peripherals via JTAG in debug situations.
        This code does not handle memorymap stuff. Use in combination with BusSlavesAggregator

        :param handle_read:
        :param handle_write:
        """

        assert callable(handle_read) and callable(handle_write)
        self.handle_read = handle_read
        self.handle_write = handle_write

    def elaborate(self, platform):
        m = Module()
        jtag = m.submodules.jtag = JTAG()
        led = platform.request("led", 0)
        m.d.comb += led.eq(1)
        led_debug = m.submodules.led_debug = BlinkDebug(Signal(), divider=18, max_value=8)
        m.submodules.in_jtag_domain = DomainRenamer("jtag")(self.elaborate_jtag_domain(platform, jtag, led_debug.value))
        return m

    def elaborate_jtag_domain(self, platform, jtag, led_debug):
        m = Module()

        write = Signal()
        addr = Signal(32)
        data = Signal(32)
        status = Signal()

        read_write_done = Signal()

        def read_write_done_callback(error):
            m.d.sync += status.eq(error)
            m.d.sync += read_write_done.eq(1)

        m.domains += ClockDomain("jtag_fsm")
        m.d.comb += ClockSignal("jtag_fsm").eq(ClockSignal())
        m.d.comb += ResetSignal("jtag_fsm").eq(jtag.reset)
        with m.FSM(domain="jtag_fsm"):
            def next_on_jtag_shift(next_state):
                with m.If(jtag.shift):
                    m.next = next_state

            with m.State("CMD"):  # we recive one bit that indicates if we want to read (0) or write (1)
                m.d.comb += led_debug.eq(0)
                m.d.sync += write.eq(jtag.tdi)
                next_on_jtag_shift("ADDR0")

            # address states
            for i in range(32):
                with m.State("ADDR{}".format(i)):
                    m.d.comb += led_debug.eq(1)
                    m.d.sync += addr[i].eq(jtag.tdi)
                    if i < 31:
                        next_on_jtag_shift("ADDR{}".format(i + 1))
                    else:
                        with m.If(write):
                            next_on_jtag_shift("WRITE0")
                        with m.Else():
                            next_on_jtag_shift("READ_WAIT")

            # read states
            with m.State("READ_WAIT"):
                m.d.comb += led_debug.eq(2)
                self.handle_read(m, addr, data, read_write_done_callback)
                with m.If(read_write_done):
                    m.d.comb += jtag.tdo.eq(1)
                    next_on_jtag_shift("READ0")
            for i in range(32):
                with m.State("READ{}".format(i)):
                    m.d.comb += led_debug.eq(3)
                    m.d.comb += jtag.tdo.eq(data[i])
                    if i < 31:
                        next_on_jtag_shift("READ{}".format(i + 1))
                    else:
                        next_on_jtag_shift("READ_STATUS")
            with m.State("READ_STATUS"):
                m.d.comb += led_debug.eq(6)
                m.d.comb += jtag.tdo.eq(status)
                next_on_jtag_shift("CMD")

            # write states
            for i in range(32):
                with m.State("WRITE{}".format(i)):
                    m.d.comb += led_debug.eq(4)
                    m.d.sync += data[i].eq(jtag.tdi)
                    if i < 31:
                        next_on_jtag_shift("WRITE{}".format(i + 1))
                    else:
                        next_on_jtag_shift("WRITE_WAIT")
            with m.State("WRITE_WAIT"):
                m.d.comb += led_debug.eq(5)
                self.handle_write(m, addr, data, read_write_done_callback)
                with m.If(read_write_done):
                    m.d.comb += jtag.tdo.eq(1)
                    next_on_jtag_shift("WRITE_STATUS")
            with m.State("WRITE_STATUS"):
                m.d.comb += led_debug.eq(6)
                m.d.comb += jtag.tdo.eq(status)
                next_on_jtag_shift("CMD")

        return m
