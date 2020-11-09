# An experiment to that checks the functionality of the axi writer

import math

from nmigen import *

from lib.peripherals.csr_bank import ControlSignal, StatusSignal
from lib.bus.axi.buffer_writer import AxiBufferWriter
from lib.bus.ring_buffer import RingBufferAddressStorage
from devices import MicroR2Platform, BetaPlatform, ZyboPlatform
from soc.platforms.zynq import ZynqSocPlatform
from soc.cli import cli
from lib.bus.stream.stream import Stream, BasicStream, PacketizedStream


class Top(Elaboratable):
    def __init__(self):
        self.reset = ControlSignal()
        self.to_write = ControlSignal(reset=32 * 1024 * 1024)
        self.data_counter = StatusSignal(32)
        self.data_valid = ControlSignal()
        self.data_ready = StatusSignal()

    def elaborate(self, platform: ZynqSocPlatform):
        m = Module()

        platform.ps7.fck_domain(requested_frequency=200e6)
        m.d.comb += ResetSignal().eq(self.reset)

        ring_buffer = RingBufferAddressStorage(buffer_size=0x1200000, n=4)

        stream = PacketizedStream(64)
        m.d.comb += self.data_ready.eq(stream.ready)
        m.d.comb += stream.valid.eq(self.data_valid)

        clock_signal = Signal()
        m.d.comb += clock_signal.eq(ClockSignal())
        axi_slave = platform.ps7.get_axi_hp_slave(clock_signal)
        axi_writer = m.submodules.axi_writer = AxiBufferWriter(ring_buffer, stream, axi_slave=axi_slave)

        with m.If(axi_writer.input.ready & axi_writer.input.valid):
            m.d.sync += self.data_counter.eq(self.data_counter + 1)
        m.d.comb += stream.payload.eq(Cat(self.data_counter, self.data_counter+1000))

        return m


if __name__ == "__main__":
    with cli(Top, runs_on=(MicroR2Platform, BetaPlatform, ZyboPlatform), possible_socs=(ZynqSocPlatform,)) as platform:
        pass
