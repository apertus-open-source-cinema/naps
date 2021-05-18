# cores for producing / receiving packets from the console

from nmigen import *
from naps import PacketizedStream, SocMemory, ControlSignal, driver_method


class ConsolePacketSource(Elaboratable):
    def __init__(self, data_width=8, max_packet_size=1024):
        self.max_packet_size = max_packet_size

        self.remaining_packet_length = ControlSignal(range(max_packet_size))
        self.packet_length = ControlSignal(range(max_packet_size))

        self.output = PacketizedStream(data_width)

    def elaborate(self, platform):
        m = Module()

        memory = m.submodules.memory = SocMemory(width=len(self.output.payload), depth=self.max_packet_size, soc_read=False)
        read_port = m.submodules.read_port = memory.read_port(domain="sync")
        with m.If(self.remaining_packet_length > 0):
            m.d.comb += self.output.ready.eq(1)
            m.d.comb += self.output.last.eq(self.remaining_packet_length == 1)
            m.d.comb += self.output.payload.eq(read_port.data)
            with m.If(self.output.valid):
                m.d.comb += read_port.en.eq(1)
                m.d.comb += read_port.addr.eq(self.packet_length - self.remaining_packet_length)
                m.d.sync += self.remaining_packet_length.eq(self.remaining_packet_length - 1)

        return m

    @driver_method
    def write_packet(self, packet):
        assert self.remaining_packet_length == 0
        for i, word in enumerate(packet):
            self.memory[i] = word
        self.packet_length = len(packet)
        self.remaining_packet_length = len(packet)



class ConsolePacketSink(Elaboratable):
    def __init__(self, input: PacketizedStream, max_packet_size=1024):
        self.max_packet_size = max_packet_size

        self.write_pointer = ControlSignal(range(self.max_packet_size))
        self.packet_done = ControlSignal()

        self.input = input

    def elaborate(self, platform):
        m = Module()

        memory = m.submodules.memory = SocMemory(width=len(self.input.payload), depth=self.max_packet_size)
        write_port = m.submodules.write_port = memory.write_port(domain="sync")
        with m.If(~self.packet_done & (self.write_pointer < self.max_packet_size)):
            m.d.comb += self.input.ready.eq(1)
            with m.If(self.input.valid):
                m.d.comb += write_port.en.eq(1)
                m.d.comb += write_port.addr.eq(self.write_pointer)
                m.d.comb += write_port.data.eq(self.input.payload)
                with m.If(self.input.last):
                    m.d.sync += self.packet_done.eq(1)

        return m

    @driver_method
    def read_packet(self):
        if not self.packet_done:
            return None

        to_return = [self.memory[i] for i in range(self.write_pointer)]
        self.write_pointer = 0
        self.packet_done = False
        return to_return
