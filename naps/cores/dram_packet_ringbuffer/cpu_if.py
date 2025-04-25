from amaranth import *
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
        self.buffer_level_list = Array([ControlSignal(range(max_packet_size), init=default_packet_size) for _ in range(n_buffers)])
        self.current_write_buffer = ControlSignal(range(n_buffers))

        for i, signal in enumerate(self.buffer_level_list):
            setattr(self, f"buffer{i}_level", signal)

    def elaborate(self, platform):
        return Module()

    # TODO: implement driver methods


class DramPacketRingbufferCpuReader(Elaboratable):
    def __init__(self, writer: DramPacketRingbufferStreamWriter):
        self.writer = writer
        self.n_buffers = writer.n_buffers

        self.current_write_buffer = StatusSignal(range(self.n_buffers))

        # note the base and level StatusSignals generated in elaborate()

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.current_write_buffer.eq(self.writer.current_write_buffer)

        for i, (base, level) in enumerate(zip(self.writer.buffer_base_list, self.writer.buffer_level_list)):
            setattr(self, f"buffer{i}_base", base) # base addresses are constant

            buffer_level = StatusSignal(level.shape())
            m.d.sync += buffer_level.eq(level)
            setattr(self, f"buffer{i}_level", buffer_level)

        return m

    @driver_method
    def read_packet_to_file(self, filename="packet.bin"):
        import os, mmap

        buf = (self.current_write_buffer - 1) % self.n_buffers
        base = getattr(self, f"buffer{buf}_base")
        length = getattr(self, f"buffer{buf}_level")

        fd = os.open("/dev/mem", os.O_RDONLY)
        with mmap.mmap(fd, length, prot=mmap.PROT_READ, offset=base) as mm:
            with open(filename, "wb") as f:
                f.write(mm)
        os.close(fd)
