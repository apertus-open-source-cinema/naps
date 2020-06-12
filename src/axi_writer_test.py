import math

from nmigen import *

from cores.csr_bank import ControlSignal, StatusSignal
from cores.axi.buffer_writer import AxiBufferWriter
from soc.zynq import ZynqSocPlatform
from soc.cli import cli


class Top(Elaboratable):
    def __init__(self):
        self.reset = ControlSignal()
        self.to_write = ControlSignal(reset=32 * 1024 * 1024)
        self.data_counter = StatusSignal(32)
        self.perf_counter = StatusSignal(32)

    def elaborate(self, platform: ZynqSocPlatform):
        m = Module()

        ps7 = platform.get_ps7()

        ps7.fck_domain(requested_frequency=200e6)
        m.d.comb += ResetSignal().eq(self.reset)

        axi_hp_port = ps7.get_axi_hp_slave(1, ClockSignal())
        axi_writer = m.submodules.axi_writer = AxiBufferWriter(axi_hp_port, [0x0f80_0000], max_buffer_size=self.to_write, max_burst_length=16)

        with m.If(axi_writer.data_ready & axi_writer.data_valid):
            m.d.sync += self.data_counter.eq(self.data_counter + 1)
        m.d.comb += axi_writer.data.eq(Cat(self.data_counter, self.data_counter+1000))

        with m.If((axi_writer.data_valid) & (axi_writer.written < (self.to_write >> int(math.log2(axi_hp_port.data_bytes))))):
            m.d.sync += self.perf_counter.eq(self.perf_counter+1)

        return m


if __name__ == "__main__":
    cli(Top)
