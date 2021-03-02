from nmigen import *
from naps import ControlSignal, StatusSignal, driver_method
from .stream_if import DramPacketRingbufferStreamWriter

__all__ = ["DramPacketRingbufferCpuReader", "DramPacketRingbufferCpuWriter"]


class DramPacketRingbufferCpuWriter(Elaboratable):
    def __init__(
            self,
            max_packet_size, n_buffers, base_address=0x0f80_0000, default_packet_size=0
    ):
        self.max_packet_size = max_packet_size
        self.base_address = base_address
        self.n_buffers = n_buffers

        self.buffer_base_list = Array([base_address + max_packet_size * i for i in range(n_buffers)])
        self.buffer_level_list = Array([ControlSignal(range(max_packet_size), reset=default_packet_size) for _ in range(n_buffers)])
        self.current_write_buffer = ControlSignal(range(n_buffers))

        for i, signal in enumerate(self.buffer_level_list):
            setattr(self, f"buffer{i}_level", signal)

    def elaborate(self, platform):
        return Module()

    # TODO: implement driver methods


class DramPacketRingbufferCpuReader(Elaboratable):
    def __init__(self, writer: DramPacketRingbufferStreamWriter):
        self.writer = writer

        m = Module()

        self.current_write_buffer = StatusSignal(range(writer.n_buffers))
        m.d.comb += self.current_write_buffer.eq(writer.current_write_buffer)

        for i, (base, level) in enumerate(zip(writer.buffer_base_list, writer.buffer_level_list)):
            print(base, level)
            buffer_base = StatusSignal(range(base + 1))
            m.d.comb += buffer_base.eq(base)
            setattr(self, f"buffer{i}_base", buffer_base)

            buffer_level = StatusSignal(level.shape())
            m.d.comb += buffer_level.eq(level)
            setattr(self, f"buffer{i}_level", buffer_level)

        self.m = m

    def elaborate(self, platform):
        return self.m

    @driver_method
    def read_packet_to_file(self, filename="packet.bin"):
        from time import sleep
        import os
        while not self.next_buffer_ready:
            sleep(0.01)

        self.current_read_buffer = self.current_read_buffer % self.num_buffers
        os.system("dd if=/dev/mem bs=4096 skip={} count={} iflag=skip_bytes,count_bytes of='{}'"
                  .format(self.current_buffer_base, self.current_buffer_length, filename))

