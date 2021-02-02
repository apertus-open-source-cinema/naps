from nmigen import *

from lib.dram_packet_ringbuffer.stream_if import DramPacketRingbufferStreamWriter
from lib.peripherals.csr_bank import ControlSignal, StatusSignal
from soc.pydriver.drivermethod import driver_method


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

        self.current_read_buffer = ControlSignal(writer.current_write_buffer.shape())
        self.next_buffer_ready = StatusSignal()
        self.current_buffer_length = StatusSignal(writer.buffer_level_list[0].shape())
        self.current_buffer_base = StatusSignal(range(writer.buffer_base_list[0] + 1))
        self.num_buffers = StatusSignal(range(writer.n_buffers + 1), reset=writer.n_buffers)

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.current_buffer_length.eq(self.writer.buffer_level_list[self.current_read_buffer])
        m.d.comb += self.current_buffer_base.eq(self.writer.buffer_base_list[self.current_read_buffer])

        with m.If(self.current_read_buffer != self.writer.current_write_buffer):
            m.d.comb += self.next_buffer_ready.eq(1)

        return m

    @driver_method
    def read_packet_to_file(self, filename="packet.bin"):
        from time import sleep
        import os
        while not self.next_buffer_ready:
            sleep(0.01)

        self.current_read_buffer = self.current_read_buffer % self.num_buffers
        os.system("dd if=/dev/mem bs=4096 skip={} count={} iflag=skip_bytes,count_bytes of='{}'"
                  .format(self.current_buffer_base, self.current_buffer_length, filename))

