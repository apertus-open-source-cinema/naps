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

        self.num_buffers = writer.n_buffers
        self.current_write_buffer = StatusSignal(self.num_buffers)
        m.d.sync += self.current_write_buffer.eq(writer.current_write_buffer)

        for i, (base, level) in enumerate(zip(writer.buffer_base_list, writer.buffer_level_list)):
            buffer_base = StatusSignal(range(base + 1))
            m.d.sync += buffer_base.eq(base)
            setattr(self, f"buffer{i}_base", buffer_base)

            buffer_level = StatusSignal(level.shape())
            m.d.sync += buffer_level.eq(level)
            setattr(self, f"buffer{i}_level", buffer_level)

        self.m = m

    def elaborate(self, platform):
        return self.m

    @driver_method
    def read_packet_to_file(self, filename="packet.bin"):
        import os

        buf = (self.current_write_buffer - 1) % self.num_buffers
        base = getattr(self, f"buffer{buf}_base")
        length = getattr(self, f"buffer{buf}_level")
        os.system(f"dd if=/dev/mem bs=4096 skip={base} count={length} iflag=skip_bytes,count_bytes of='{filename}'")
