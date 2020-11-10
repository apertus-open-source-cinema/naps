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

    def elaborate(self, platform):
        m = Module()

        with m.If(self.stream.valid & ~self.stream.ready):
            m.d.sync += self.valid_not_ready.eq(self.valid_not_ready + 1)
        with m.If(self.stream.ready & ~self.stream.ready):
            m.d.sync += self.ready_not_valid.eq(self.ready_not_valid + 1)

        m.d.sync += self.reference_counter.eq(self.reference_counter + 1)
        with m.If(self.stream.valid & self.stream.ready):
            m.d.sync += self.successful_transactions_counter.eq(self.successful_transactions_counter + 1)

            for name, signal in self.stream.payload_signals.items():
                if len(signal) == 1:
                    count = StatusSignal(32)
                    cycle_counter = Signal(32)
                    m.d.sync += cycle_counter.eq(cycle_counter + 1)
                    cycle_length = StatusSignal(32)
                    with m.If(signal):
                        m.d.sync += count.eq(count + 1)
                        m.d.sync += cycle_counter.eq(0)
                        m.d.sync += cycle_length.eq(cycle_counter + 1)
                    setattr(self, "{}_cycle_length".format(name), cycle_length)
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

