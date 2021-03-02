# An experiment to that checks the functionality of the axi writer
from nmigen import *
from naps import *


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

        stream = PacketizedStream(64)
        m.d.comb += self.data_ready.eq(stream.ready)
        m.d.comb += stream.valid.eq(self.data_valid)

        axi_writer = m.submodules.axi_writer = DramPacketRingbufferStreamWriter(stream, max_packet_size=0x1200000, n_buffers=4)

        with m.If(axi_writer.input.ready & axi_writer.input.valid):
            m.d.sync += self.data_counter.eq(self.data_counter + 1)
        m.d.comb += stream.payload.eq(Cat(self.data_counter, self.data_counter + 1000))

        return m


if __name__ == "__main__":
    cli(Top, runs_on=(MicroR2Platform, BetaPlatform, ZyboPlatform), possible_socs=(ZynqSocPlatform,))
