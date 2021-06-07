from nmigen import *

from naps import ImageStream, PacketizedStream, process_write_to_stream, ControlSignal, StreamGearbox, Process, process_delay, StatusSignal
from .py_dsi_generator import assemble, short_packet, ShortPacketDataType, LongPacketDataType, blanking


class ImageStream2MipiDsiVideoBurstMode(Elaboratable):
    def __init__(self, input: ImageStream, num_lanes: int, image_width=480):
        self.input = input
        self.num_lanes = num_lanes
        self.line_width = ControlSignal(16, reset=image_width * 3)

        self.gearbox_not_ready = StatusSignal(32)

        self.vbp = ControlSignal(16, reset=18)
        self.vfp = ControlSignal(16, reset=4)
        self.hbp = ControlSignal(16, reset=100)
        self.hfp = ControlSignal(16, reset=100)
        self.v_dummy_line = ControlSignal(32, reset=10000)

        self.output = PacketizedStream(num_lanes * 8)

    def elaborate(self, platform):
        m = Module()

        gearbox = m.submodules.gearbox = StreamGearbox(self.input, target_width=len(self.output.payload))

        def repack_to_lanes(packet_bytes):
            values = [Const(b, 8) for b in packet_bytes]
            if self.num_lanes == 1:
                pass
            elif self.num_lanes == 2:
                values = [
                    Cat(values[0:2]),
                    Cat(values[2:4]),
                ]
            elif self.num_lanes == 4:
                values = Cat(values)
            else:
                raise AssertionError("Invalid number of lanes!")
            return [(v, i == len(values) - 1) for i, v in enumerate(values)]

        def short_packet_words(type, payload=Const(0, 16)):
            return repack_to_lanes(assemble(short_packet(type, payload)))

        frame_last = Signal()
        v_porch_counter = Signal(16)

        def v_porch(name, to, length):
            with Process(m, name, to=None) as p:
                p += process_delay(m, self.hbp)
                for value, last in short_packet_words(ShortPacketDataType.H_SYNC_START):
                    p += process_write_to_stream(m, self.output, payload=value, last=last)
                p += process_delay(m, self.v_dummy_line)
                p += process_delay(m, self.hfp)
                with m.If(v_porch_counter < length):
                    m.d.sync += v_porch_counter.eq(v_porch_counter + 1)
                    m.next = name
                with m.Else():
                    m.d.sync += v_porch_counter.eq(0)
                    m.next = to

        with m.FSM():
            with Process(m, "VSYNC", to="VBP") as p:
                for value, last in short_packet_words(ShortPacketDataType.V_SYNC_START):
                    p += process_write_to_stream(m, self.output, payload=value, last=last)

            v_porch("VBP", "HSYNC", self.vbp)

            with Process(m, "HSYNC", to="LINE_HEADER") as p:
                p += process_delay(m, self.hbp)
                for value, last in short_packet_words(ShortPacketDataType.H_SYNC_START):
                    p += process_write_to_stream(m, self.output, payload=value, last=last)

            with Process(m, "LINE_HEADER", to="LINE_DATA") as p:
                p += m.If(gearbox.output.valid)
                for value, last in short_packet_words(LongPacketDataType.PACKED_PIXEL_STREAM_24_BIT_RGB_8_8_8, self.line_width):
                    p += process_write_to_stream(m, self.output, payload=value)
            with m.State("LINE_DATA"):
                with m.If(gearbox.output.line_last & gearbox.output.valid & gearbox.output.ready):
                    m.next = "LINE_FOOTER"
                    m.d.sync += frame_last.eq(gearbox.output.frame_last)
                with m.If(~gearbox.output.valid):
                    m.d.sync += self.gearbox_not_ready.eq(self.gearbox_not_ready + 1)
                m.d.comb += self.output.connect_upstream(gearbox.output, allow_partial=True)
            with Process(m, "LINE_FOOTER", to="LINE_END") as p:
                for value, last in repack_to_lanes([0x0, 0x0]):
                    p += process_write_to_stream(m, self.output, payload=value, last=last)

            with m.State("LINE_END"):
                with m.If(frame_last):
                    m.next = "VFP"
                with m.Else():
                    with process_delay(m, self.hfp):
                        m.next = "HSYNC"

            v_porch("VFP", "VSYNC", self.vfp)


        return m
