from nmigen import *

from naps import PacketizedStream, process_write_to_stream, ControlSignal, Process, process_delay, StatusSignal
from naps.cores import ImageStream, StreamGearbox, probe, fsm_probe, trigger
from .py_dsi_generator import assemble, short_packet
from .types import DsiShortPacketDataType, DsiLongPacketDataType

__all__ = ["ImageStream2Dsi"]


class ImageStream2Dsi(Elaboratable):
    """
    Conoverts an ImageStream to a Packetized stream that can be fed into a DSI phy.
    Uses Non Burst Mode with Sync Events.
    """
    def __init__(self, input: ImageStream, num_lanes: int, image_width=480):
        assert len(input.payload) == 24
        self.input = input
        self.num_lanes = num_lanes
        self.line_width = ControlSignal(16, reset=image_width * 3)

        self.gearbox_not_ready = StatusSignal(32)

        self.vbp = ControlSignal(16, reset=18)
        self.vfp = ControlSignal(16, reset=4)
        self.vsync_width = ControlSignal(16)
        self.hbp = 68
        self.hfp = 20
        self.hsync_width = ControlSignal(16)
        self.v_dummy_line = ControlSignal(32, reset=480 * 2)

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

        def send_short_packet(p, type, payload=Const(0, 16), lp_after=False):
            for value, last in short_packet_words(type, payload):
                p += process_write_to_stream(m, self.output, payload=value, last=last & lp_after)

        def end_of_transmisson(p):
            send_short_packet(p, DsiShortPacketDataType.END_OF_TRANSMISSION_PACKET, lp_after=True)

        def blanking(p, length, omit_footer=False):
            send_short_packet(p, DsiLongPacketDataType.BLANKING_PACKET_NO_DATA, Const(length, 16))
            for i in range((length // 2)):
                p += process_write_to_stream(m, self.output, payload=0x0)
            if not omit_footer:
                p += process_write_to_stream(m, self.output, payload=0x0)  # checksum


        frame_last = Signal()
        v_porch_counter = Signal(16)

        def v_porch(name, to, length, skip_first_hsync=False):
            if not skip_first_hsync:
                first_name = name
                second_process_name = f"{name}_OVERHEAD"
            else:
                first_name = f"{name}_HSYNC"
                second_process_name = name

            with Process(m, first_name, to=second_process_name) as p:
                send_short_packet(p, DsiShortPacketDataType.H_SYNC_START)
                end_of_transmisson(p)

            with Process(m, second_process_name, to=None) as p:
                p += process_delay(m, self.hbp)
                p += process_delay(m, self.v_dummy_line)
                p += process_delay(m, self.hfp)
                with m.If(v_porch_counter < length):
                    m.d.sync += v_porch_counter.eq(v_porch_counter + 1)
                    m.next = first_name
                with m.Else():
                    m.d.sync += v_porch_counter.eq(0)
                    m.next = to

        probe(m, self.output.valid)
        probe(m, self.output.ready)
        probe(m, self.output.payload)
        
        trig = Signal()
        trigger(m, trig)

        with m.FSM() as fsm:
            fsm_probe(m, fsm)

            with Process(m, "VSYNC", to="VBP") as p:
                p += m.If(gearbox.output.valid)
                send_short_packet(p, DsiShortPacketDataType.V_SYNC_START)
                end_of_transmisson(p)

            v_porch("VBP", "LINE_START", self.vbp, skip_first_hsync=True)

            with Process(m, "LINE_START", to="LINE_DATA") as p:
                m.d.comb += trig.eq(1)
                send_short_packet(p, DsiShortPacketDataType.H_SYNC_START)
                blanking(p, self.hbp * 3)
                send_short_packet(p, DsiLongPacketDataType.PACKED_PIXEL_STREAM_24_BIT_RGB_8_8_8, self.line_width)
            with m.State("LINE_DATA"):
                with m.If(gearbox.output.line_last & gearbox.output.valid & gearbox.output.ready):
                    m.next = "LINE_END"
                    m.d.sync += frame_last.eq(gearbox.output.frame_last)
                with m.If(~gearbox.output.valid):
                    m.d.sync += self.gearbox_not_ready.eq(self.gearbox_not_ready + 1)
                m.d.comb += self.output.connect_upstream(gearbox.output, allow_partial=True)
            with Process(m, "LINE_END", to=None) as p:
                p += process_write_to_stream(m, self.output, payload=0x0)  # TODO: handle the non 2 lane case
                blanking(p, self.hfp * 3, omit_footer=True)  # we omit the footer to be able to do dispatch the next state with zero cycle delay
                with process_write_to_stream(m, self.output, payload=0x0):
                    with m.If(frame_last):
                        m.next = "VFP"
                    with m.Else():
                        m.next = "LINE_START"

            v_porch("VFP", "VSYNC", self.vfp)


        return m
