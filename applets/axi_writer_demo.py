# An experiment to that checks the functionality of the axi writer
from nmigen import *
from naps import *


class Top(Elaboratable):
    def __init__(self):
        self.reset = ControlSignal()
        self.to_write = ControlSignal(32)
        self.needed_cycles = StatusSignal(32)
        self.packet_size = ControlSignal(32, reset=1 * 1024 * 1024)
        self.data_counter = StatusSignal(32)
        self.packet_counter = StatusSignal(32)
        self.data_ready = StatusSignal()

    def elaborate(self, platform: ZynqSocPlatform):
        m = Module()

        platform.ps7.fck_domain(requested_frequency=200e6)
        m.d.comb += ResetSignal().eq(self.reset)

        stream = PacketizedStream(64)
        m.d.comb += self.data_ready.eq(stream.ready)

        done = Signal(reset = 0)

        axi_writer = m.submodules.axi_writer = DramPacketRingbufferStreamWriter(stream, max_packet_size=0x1200000, n_buffers=4)
        self.axi_writer = axi_writer


        with m.If(~done):
            m.d.sync += self.needed_cycles.eq(self.needed_cycles + 1)
            m.d.comb += stream.valid.eq(1)

        with m.If(((self.packet_counter + 1) == self.packet_size) | ((self.data_counter + 1) == self.to_write)):
            m.d.comb += stream.last.eq(1)


        with m.If(axi_writer.input.ready & axi_writer.input.valid):
            with m.If((self.data_counter + 1) < self.to_write):
                m.d.sync += self.data_counter.eq(self.data_counter + 1)
            with m.Else():
                m.d.sync += self.data_counter.eq(0)
                m.d.sync += done.eq(1)

            with m.If((self.packet_counter + 1) == self.packet_size):
                m.d.sync += self.packet_counter.eq(0)
            with m.Else():
                m.d.sync += self.packet_counter.eq(self.packet_counter + 1)

        m.d.comb += stream.payload.eq(Cat(self.data_counter, self.data_counter + 1000))

        return m

    @driver_method
    def run_and_check(self, to_write = 4 * 1024 * 1024, packet_size = 1 * 1024 * 1024):
        self.reset = 1
        self.to_write = to_write
        self.packet_size = packet_size
        self.reset = 0

        import time
        time.sleep(0.5)

        print(f"efficiency: {self.to_write / self.needed_cycles}")

        written_buffers = (to_write + packet_size - 1) // packet_size
        assert self.axi_writer.buffers_written == written_buffers

        base_address = self.axi_writer.base_address
        max_buffer = max(self.axi_writer.buffer_base_list_cpu)
        map_len = max_buffer + packet_size * 8 - base_address

        import mmap, os, sys
        mem = mmap.mmap(
            os.open('/dev/mem', os.O_RDWR | os.O_SYNC),
            map_len, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE,
            offset = base_address
        )

        last = (written_buffers - 4) * packet_size - 1
        offs = written_buffers % self.axi_writer.n_buffers
        bufs = self.axi_writer.buffer_base_list_cpu[offs:] + self.axi_writer.buffer_base_list_cpu[:offs]
        for buf_addr in bufs:
            for w in range(packet_size):
                if w % 1000 == 0:
                    print(".", end="")
                    sys.stdout.flush()
                addr = buf_addr - base_address + 8 * w
                val = int.from_bytes(mem[addr:addr+8], 'little')
                lower = val & ((1 << 32) - 1)
                upper = val >> 32
                # print(lower, upper, last)
                assert lower == last + 1, f"[{buf_addr:08x}, {w:08x}]: {lower} != {last} + 1"
                assert upper == lower + 1000, f"[{buf_addr:0x8}, {w:08x}]: {upper} != {lower} + 1000"
                last = lower
            print()



if __name__ == "__main__":
    cli(Top, runs_on=(MicroR2Platform, BetaPlatform, ZyboPlatform), possible_socs=(ZynqSocPlatform,))
