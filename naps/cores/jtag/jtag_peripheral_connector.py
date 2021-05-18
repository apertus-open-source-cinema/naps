from nmigen import *
from naps.vendor import JTAG

__all__ = ["JTAGPeripheralConnector"]


class JTAGPeripheralConnector(Elaboratable):
    def __init__(self, peripheral, jtag=None, jtag_domain="jtag"):
        """
        A simple `PeripheralConnector` implementation for querying `Peripheral`s via JTAG in debug situations.
        This code does not handle memorymap stuff. Use in combination with PeripheralsAggregator
        """

        assert callable(peripheral.handle_read) and callable(peripheral.handle_write)
        assert isinstance(peripheral.range(), range)
        self.peripheral = peripheral
        self.jtag = jtag
        self.jtag_domain = jtag_domain

    def elaborate(self, platform):
        m = Module()
        if not self.jtag:
            jtag = m.submodules.jtag = JTAG(self.jtag_domain)
        else:
            jtag = self.jtag

        address_range = self.peripheral.range()
        state = Signal(range(10))

        addr = Signal(32)
        data = Signal(32)
        status = Signal()

        read_write_done = Signal()

        def read_write_done_callback(error):
            m.d.sync += status.eq(error)
            m.d.sync += read_write_done.eq(1)

        # This FSM should has two important properties:
        # 1) It can be controlled with an unknown latency on both tdi and tdo
        # 2) When it is in an unknown state we can return to a defined state (IDLE0) by shifting in "0" for 96 cycles
        # READ:
        # <0>*<1>(ADDRESS[32])<0><1 keep high>
        #                                             <1>(DATA[32])(STATUS_BIT[1])
        # WRITE:
        # <0>*<1>(ADDRESS[32])<1>(DATA[32])
        #                                             <1>(STATUS_BIT[1])
        with m.FSM():
            def next_on_jtag_shift(next_state, use_tdo_shift=False):
                with m.If(jtag.shift_tdo if use_tdo_shift else jtag.shift_tdi):
                    m.next = next_state

            with m.State("IDLE0"):
                m.d.comb += state.eq(0)
                m.d.sync += read_write_done.eq(0)
                with m.If(~jtag.tdi):  # in IDLE0 IDLE1 we wait for a 0->1 transition to have property 2) (see above)
                    next_on_jtag_shift("IDLE1")
            with m.State("IDLE1"):
                m.d.comb += state.eq(1)
                with m.If(jtag.tdi):
                    next_on_jtag_shift("ADDR0")

            # address states
            for i in range(32):
                with m.State("ADDR{}".format(i)):
                    m.d.comb += state.eq(2)
                    m.d.sync += addr[i].eq(jtag.tdi)
                    if i < 31:
                        next_on_jtag_shift("ADDR{}".format(i + 1))
                    else:
                        next_on_jtag_shift("RW_CMD")

            with m.State("RW_CMD"):  # we receive one bit that indicates if we want to read (0) or write (1)
                m.d.sync += data.eq(0)
                m.d.comb += state.eq(3)
                with m.If(jtag.tdi):
                    next_on_jtag_shift("WRITE0")
                with m.Else():
                    next_on_jtag_shift("READ_WAIT")

            # read states
            with m.State("READ_WAIT"):
                m.d.comb += state.eq(4)
                with m.If(read_write_done):
                    m.d.comb += jtag.tdo.eq(1)
                    next_on_jtag_shift("READ0")
                with m.Else():
                    self.peripheral.handle_read(m, addr - address_range.start, data, read_write_done_callback)
                with m.If(~jtag.tdi):  # we are requested to abort the waiting
                    next_on_jtag_shift("IDLE0")
            for i in range(32):
                with m.State("READ{}".format(i)):
                    m.d.comb += state.eq(5)
                    m.d.comb += jtag.tdo.eq(data[i])
                    if i < 31:
                        next_on_jtag_shift("READ{}".format(i + 1), use_tdo_shift=True)
                    else:
                        next_on_jtag_shift("READ_STATUS")
            with m.State("READ_STATUS"):
                m.d.comb += state.eq(6)
                m.d.comb += jtag.tdo.eq(status)
                next_on_jtag_shift("IDLE0")

            # write states
            for i in range(32):
                with m.State("WRITE{}".format(i)):
                    m.d.comb += state.eq(7)
                    m.d.sync += data[i].eq(jtag.tdi)
                    if i < 31:
                        next_on_jtag_shift("WRITE{}".format(i + 1))
                    else:
                        next_on_jtag_shift("WRITE_WAIT")
            with m.State("WRITE_WAIT"):
                m.d.comb += state.eq(8)
                with m.If(read_write_done):
                    m.d.comb += jtag.tdo.eq(1)
                    next_on_jtag_shift("WRITE_STATUS")
                with m.Else():
                    self.peripheral.handle_write(m, addr - address_range.start, data, read_write_done_callback)
                with m.If(~jtag.tdi):  # we are requested to abort the waiting
                    next_on_jtag_shift("IDLE0")
            with m.State("WRITE_STATUS"):
                m.d.comb += state.eq(9)
                m.d.comb += jtag.tdo.eq(status)
                next_on_jtag_shift("IDLE0")

        if self.jtag_domain != "sync":
            return DomainRenamer(self.jtag_domain)(m)
        else:
            return m
