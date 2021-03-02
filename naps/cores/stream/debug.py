from nmigen import *
from naps import Stream, StatusSignal, driver_property

__all__ = ["StreamInfo", "InflexibleSinkDebug", "InflexibleSourceDebug"]


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

        with m.If(self.stream.valid & ~self.stream.ready):
            m.d.sync += self.valid_not_ready.eq(self.valid_not_ready + 1)
        with m.If(self.stream.ready & ~self.stream.valid):
            m.d.sync += self.ready_not_valid.eq(self.ready_not_valid + 1)

        m.d.sync += self.reference_counter.eq(self.reference_counter + 1)

        transaction = Signal()
        m.d.comb += transaction.eq(self.stream.valid & self.stream.ready)
        with m.If(transaction):
            m.d.sync += self.successful_transactions_counter.eq(self.successful_transactions_counter + 1)

        m.d.comb += self.current_ready.eq(self.stream.ready)
        m.d.comb += self.current_valid.eq(self.stream.valid)

        for name, signal in self.stream.payload_signals.items():
            if len(signal) == 1:
                m.submodules[name] = MetadataSignalDebug(signal, transaction)
            else:
                current_state = StatusSignal(signal.shape())
                m.d.comb += current_state.eq(signal)
                setattr(self, "current_{}".format(name), current_state)
                last_transaction_state = StatusSignal(signal.shape())
                with m.If(transaction):
                    m.d.sync += last_transaction_state.eq(signal)
                setattr(self, "last_transaction_{}".format(name), last_transaction_state)

        return m

    @driver_property
    def efficiency_percent(self):
        return self.successful_transactions_counter / self.reference_counter * 100

    @driver_property
    def stall_source_percent(self):
        return self.ready_not_valid / self.reference_counter * 100

    @driver_property
    def stall_sink_percent(self):
        return self.valid_not_ready / self.reference_counter * 100

    @driver_property
    def stall_both_percent(self):
        return (100 - self.efficiency_percent) - self.stall_source_percent - self.stall_sink_percent


class MetadataSignalDebug(Elaboratable):
    def __init__(self, signal, transaction):
        assert len(signal) == 1
        self.signal = signal
        self.transaction = transaction

        self.cycle_1_length = StatusSignal(32)
        self.cycle_1_length_changed = StatusSignal(32)
        self.cycle_0_length = StatusSignal(32)
        self.cycle_0_length_changed = StatusSignal(32)
        self.cycles = StatusSignal(32)
        self.current = StatusSignal()

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.current.eq(self.signal)

        cycle_0_counter = Signal(32)
        cycle_1_counter = Signal(32)

        with m.If(self.transaction):
            with m.If(self.signal):
                m.d.sync += cycle_0_counter.eq(0)
                with m.If(cycle_0_counter != 0):
                    m.d.sync += self.cycle_0_length.eq(cycle_0_counter)
                    with m.If(self.cycle_0_length != cycle_0_counter):
                        m.d.sync += self.cycle_0_length_changed.eq(self.cycle_0_length_changed + 1)
                m.d.sync += cycle_1_counter.eq(cycle_1_counter + 1)
            with m.Else():
                m.d.sync += cycle_1_counter.eq(0)
                with m.If(cycle_1_counter != 0):
                    m.d.sync += self.cycle_1_length.eq(cycle_1_counter)
                    with m.If(self.cycle_1_length != cycle_1_counter):
                        m.d.sync += self.cycle_1_length_changed.eq(self.cycle_1_length_changed + 1)
                m.d.sync += cycle_0_counter.eq(cycle_0_counter + 1)

            signal_last = Signal()
            m.d.sync += signal_last.eq(self.signal)
            with m.If(self.signal & ~signal_last):
                m.d.sync += self.cycles.eq(self.cycles + 1)

        return m

    @driver_property
    def cycle_length(self):
        return self.cycle_0_length + self.cycle_1_length


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
