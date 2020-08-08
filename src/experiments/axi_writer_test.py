# An experiment to that checks the functionality of the axi writer

import math

from nmigen import *

from cores.csr_bank import ControlSignal, StatusSignal
from cores.axi.buffer_writer import AxiBufferWriter
from cores.ring_buffer_address_storage import RingBufferAddressStorage
from devices import MicroR2Platform, BetaPlatform, ZyboPlatform
from util.stream import StreamEndpoint
from soc.platforms.zynq import ZynqSocPlatform
from soc.cli import cli


class Top(Elaboratable):
    def __init__(self):
        self.reset = ControlSignal()
        self.to_write = ControlSignal(reset=32 * 1024 * 1024)
        self.data_counter = StatusSignal(32)
        self.perf_counter = StatusSignal(32)
        self.data_valid = ControlSignal()
        self.data_ready = StatusSignal()

    def elaborate(self, platform: ZynqSocPlatform):
        m = Module()

        platform.ps7.fck_domain(requested_frequency=200e6)
        m.d.comb += ResetSignal().eq(self.reset)

        ring_buffer = RingBufferAddressStorage(buffer_size=0x1200000, n=4)

        stream_source = StreamEndpoint(Signal(64), is_sink=False, has_last=True)
        m.d.comb += self.data_ready.eq(stream_source.ready)
        m.d.comb += stream_source.valid.eq(self.data_valid)

        clock_signal = Signal()
        m.d.comb += clock_signal.eq(ClockSignal())
        axi_slave = platform.ps7.get_axi_hp_slave(clock_signal)
        axi_writer = m.submodules.axi_writer = AxiBufferWriter(ring_buffer, stream_source, axi_slave=axi_slave)

        with m.If(axi_writer.stream_source.ready & axi_writer.stream_source.valid):
            m.d.sync += self.data_counter.eq(self.data_counter + 1)
        m.d.comb += stream_source.payload.eq(Cat(self.data_counter, self.data_counter+1000))

        with m.If((stream_source.valid) & (axi_writer.words_written < (self.to_write >> int(math.log2(axi_slave.data_bytes))))):
            m.d.sync += self.perf_counter.eq(self.perf_counter+1)

        return m


if __name__ == "__main__":
    with cli(Top, runs_on=(MicroR2Platform, BetaPlatform, ZyboPlatform)) as platform:
        pass
