# cores for producing / receiving packets from the console

from nmigen import *
from nmigen.lib.cdc import FFSynchronizer
from nmigen.utils import bits_for

from naps import PacketizedStream, ControlSignal, driver_method, StatusSignal, Changed
from ..stream import StreamMemoryReader, StreamBuffer
from ..peripherals import SocMemory


__all__ = ["ConsolePacketSource", "ConsolePacketSink"]


class ConsolePacketSource(Elaboratable):
    def __init__(self, data_width=8, max_packet_size=1024):
        self.max_packet_size = max_packet_size

        self.reset = ControlSignal()
        self.packet_length = ControlSignal(range(max_packet_size))
        self.read_ptr = StatusSignal(range(max_packet_size))
        self.done = StatusSignal(reset=1)
        self.memory = SocMemory(
            width=data_width, depth=self.max_packet_size,
            soc_read=False,  attrs=dict(syn_ramstyle="block_ram")
        )

        self.output = PacketizedStream(data_width)

    def elaborate(self, platform):
        m = Module()

        memory = m.submodules.memory = self.memory

        address_stream = PacketizedStream(bits_for(self.max_packet_size))
        with m.If(~self.done):
            m.d.comb += address_stream.valid.eq(1)
            m.d.comb += address_stream.last.eq(self.read_ptr == self.packet_length)
            m.d.comb += address_stream.payload.eq(self.read_ptr)
            with m.If(address_stream.ready):
                m.d.sync += self.read_ptr.eq(self.read_ptr + 1)
                m.d.sync += self.done.eq(self.read_ptr == self.packet_length)

        reset = Signal()
        m.submodules += FFSynchronizer(self.reset, reset)
        with m.If(Changed(m, reset)):
            m.d.sync += self.read_ptr.eq(0)
            m.d.sync += self.done.eq(0)

        reader = m.submodules.reader = StreamMemoryReader(address_stream, memory)
        buffer = m.submodules.buffer = StreamBuffer(reader.output)
        m.d.comb += self.output.connect_upstream(buffer.output)

        return m

    @driver_method
    def write_packet(self, packet, timeout=0):
        from time import sleep
        for i in range(int(timeout * 10)):
            if self.done:
                break
            sleep(0.1)
        assert self.done
        for i, word in enumerate(packet):
            self.memory[i] = word
        self.packet_length = len(packet) - 1
        self.reset = not self.reset



class ConsolePacketSink(Elaboratable):
    def __init__(self, input: PacketizedStream, max_packet_size=1024):
        self.max_packet_size = max_packet_size

        self.reset = ControlSignal()
        self.write_pointer = StatusSignal(range(self.max_packet_size))
        self.packet_done = StatusSignal()
        self.memory = SocMemory(
            width=len(input.payload), depth=self.max_packet_size,
            soc_write=False, attrs=dict(syn_ramstyle="block_ram")
        )

        self.input = input

    def elaborate(self, platform):
        m = Module()

        memory = m.submodules.memory = self.memory
        write_port = m.submodules.write_port = memory.write_port(domain="sync")
        with m.If(~self.packet_done & (self.write_pointer < self.max_packet_size)):
            m.d.comb += self.input.ready.eq(1)
            with m.If(self.input.valid):
                m.d.comb += write_port.en.eq(1)
                m.d.comb += write_port.addr.eq(self.write_pointer)
                m.d.comb += write_port.data.eq(self.input.payload)
                m.d.sync += self.write_pointer.eq(self.write_pointer + 1)
                with m.If(self.input.last):
                    m.d.sync += self.packet_done.eq(1)

        reset = Signal()
        m.submodules += FFSynchronizer(self.reset, reset)
        with m.If(Changed(m, reset)):
            m.d.sync += self.write_pointer.eq(0)
            m.d.sync += self.packet_done.eq(0)


        return m

    @driver_method
    def read_packet(self, timeout=0):
        from time import sleep
        for i in range(int(timeout * 10)):
            if self.packet_done:
                break
            sleep(0.1)
        if not self.packet_done:
            return None

        to_return = [self.memory[i] for i in range(self.write_pointer)]
        self.reset = not self.reset
        return to_return

