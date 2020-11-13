from nmigen import *

from lib.bus.stream.stream import Stream
from lib.peripherals.csr_bank import StatusSignal


class StreamInfo(Elaboratable):
    def __init__(self, stream: Stream):
        self.stream = stream

        self.reference_counter = StatusSignal(32)
        self.successful_transactions_counter = StatusSignal(32)
        self.ready_not_valid = StatusSignal(32)
        self.valid_not_ready = StatusSignal(32)
        self.current_ready = StatusSignal()
        self.current_valid = StatusSignal()

    def elaborate(self, platform):
        m = Module()
        if hasattr(platform, "debug") and not platform.debug:
            return m

        m.d.comb += self.current_ready.eq(self.stream.ready)
        m.d.comb += self.current_valid.eq(self.stream.valid)

        for k, s in self.stream.payload_signals.items():
            current_state = StatusSignal(s.shape())
            m.d.comb += current_state.eq(s)
            setattr(self, "current_{}".format(k), current_state)

        with m.If(self.stream.valid & ~self.stream.ready):
            m.d.sync += self.valid_not_ready.eq(self.valid_not_ready + 1)
        with m.If(self.stream.ready & ~self.stream.ready):
            m.d.sync += self.ready_not_valid.eq(self.ready_not_valid + 1)

        m.d.sync += self.reference_counter.eq(self.reference_counter + 1)
        with m.If(self.stream.valid & self.stream.ready):
            m.d.sync += self.successful_transactions_counter.eq(self.successful_transactions_counter + 1)

            for name, signal in self.stream.payload_signals.items():
                if len(signal) == 1:
                    cycle_0_length = StatusSignal(32)
                    cycle_0_length_changed = StatusSignal(32)
                    cycle_0_counter = Signal(32)
                    cycle_1_length = StatusSignal(32)
                    cycle_1_length_changed = StatusSignal(32)
                    cycle_1_counter = Signal(32)

                    with m.If(signal):
                        m.d.sync += cycle_0_counter.eq(0)
                        with m.If(cycle_0_counter != 0):
                            m.d.sync += cycle_0_length.eq(cycle_0_counter)
                            with m.If(cycle_0_length != cycle_0_counter):
                                m.d.sync += cycle_0_length_changed.eq(cycle_0_length_changed + 1)
                        m.d.sync += cycle_1_counter.eq(cycle_1_counter + 1)
                    with m.Else():
                        m.d.sync += cycle_1_counter.eq(0)
                        with m.If(cycle_1_counter != 0):
                            m.d.sync += cycle_1_length.eq(cycle_1_counter)
                            with m.If(cycle_1_length != cycle_1_counter):
                                m.d.sync += cycle_1_length_changed.eq(cycle_1_length_changed + 1)
                        m.d.sync += cycle_0_counter.eq(cycle_0_counter + 1)

                    count = StatusSignal(32)
                    signal_last = Signal()
                    m.d.sync += signal_last.eq(signal)
                    with m.If(signal & ~signal_last):
                        m.d.sync += count.eq(count + 1)

                    setattr(self, "{}_cycle_0_length".format(name), cycle_0_length)
                    setattr(self, "{}_cycle_0_length_changed".format(name), cycle_0_length_changed)
                    setattr(self, "{}_cycle_1_length".format(name), cycle_1_length)
                    setattr(self, "{}_cycle_1_length_changed".format(name), cycle_1_length_changed)
                    setattr(self, "{}_count".format(name), count)

        return m


class InflexibleSourceDebug(Elaboratable):
    def __init__(self, stream):
        self.stream = stream
        self.dropped = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()
        
        with m.If(self.stream.valid & ~self.stream.ready):
            m.d.sync += self.dropped.eq(self.dropped + 1)

        return m


class InflexibleSinkDebug(Elaboratable):
    def __init__(self, stream):
        self.stream = stream
        self.invalid = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        with m.If(self.stream.ready & ~self.stream.valid):
            m.d.sync += self.invalid.eq(self.invalid + 1)

        return m

