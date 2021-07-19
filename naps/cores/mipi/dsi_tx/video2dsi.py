from nmigen import *

from naps import PacketizedStream, process_write_to_stream, ControlSignal, Process, StatusSignal
from naps.cores import ImageStream, StreamGearbox, probe, fsm_probe, trigger, fsm_status_reg, StreamInfo
from .types import DsiShortPacketDataType, DsiLongPacketDataType
from .. import PacketHeader, DataIdentifier

__all__ = ["ImageStream2Dsi"]


class ImageStream2Dsi(Elaboratable):
    """
    Converts an ImageStream to a Packetized stream that can be fed into a DSI phy.
    Uses Non Burst Mode with Sync Events.
    """
    def __init__(self, input: ImageStream, num_lanes: int, image_width=480, debug=False):
        assert len(input.payload) == 24
        self.input = input
        self.num_lanes = num_lanes
        self.image_width = ControlSignal(16, reset=image_width * 3)
        self.debug = debug

        self.vbp = ControlSignal(16, reset=18)
        self.vfp = ControlSignal(16, reset=4)
        self.hbp = ControlSignal(16, reset=68 * 3)
        self.hfp = ControlSignal(16, reset=20 * 3)

        self.gearbox_not_ready = StatusSignal(32)

        self.output = PacketizedStream(num_lanes * 8)

    def elaborate(self, platform):
        m = Module()

        gearbox = m.submodules.gearbox = StreamGearbox(self.input, target_width=len(self.output.payload))

        def repack_to_lanes(packet):
            values = [packet[i*8: (i+1)*8] for i in range(len(packet) // 8)]
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
            data_id = DataIdentifier(data_type=type, virtual_channel_identifier=0)
            packet_prelim = PacketHeader(data_id=data_id, word_count=payload, ecc=0)
            packet = PacketHeader(data_id=data_id, word_count=payload, ecc=packet_prelim.calculate_ecc())
            return repack_to_lanes(packet.as_value())

        def send_short_packet(p, type, payload=Const(0, 16), lp_after=False):
            for value, last in short_packet_words(type, payload):
                p += process_write_to_stream(m, self.output, payload=value, last=last & lp_after)

        def end_of_transmission(p):
            send_short_packet(p, DsiShortPacketDataType.END_OF_TRANSMISSION_PACKET, lp_after=True)


        blanking_counter = Signal(16)
        is_ready = Signal()

        def blanking(p, length, omit_footer=False, type=DsiLongPacketDataType.BLANKING_PACKET_NO_DATA):
            length_without_overhead = length - 6
            m.d.sync += blanking_counter.eq(0)
            if not isinstance(length_without_overhead, Value):
                length_without_overhead = Const(length_without_overhead, 16)
            send_short_packet(p, type, length_without_overhead[0:16])
            with process_write_to_stream(m, self.output, payload=0x0):
                m.d.sync += blanking_counter.eq(blanking_counter + 1)
                m.d.comb += is_ready.eq(1)
            p += m.If(blanking_counter + is_ready >= length_without_overhead // 2)  # the packet overhead is 6 bytes (4 header and 2 footer)
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

            with Process(m, second_process_name, to=None) as p:
                blanking(p, self.hfp + self.image_width + self.hbp, type=DsiLongPacketDataType.NULL_PACKET_NO_DATA, omit_footer=True)
                with process_write_to_stream(m, self.output, payload=0x0):
                    with m.If(v_porch_counter < length):
                        m.d.sync += v_porch_counter.eq(v_porch_counter + 1)
                        m.next = first_name
                    with m.Else():
                        m.d.sync += v_porch_counter.eq(0)
                        m.next = to

        trig = Signal()
        if self.debug and False:
            probe(m, self.output.valid)
            probe(m, self.output.ready)
            probe(m, self.output.last)
            probe(m, self.output.payload)
            probe(m, gearbox.output.ready)
            probe(m, gearbox.output.valid)
            probe(m, gearbox.output.frame_last)
            probe(m, gearbox.output.line_last)
            probe(m, gearbox.output.payload)

            # trigger(m, trig)

        with m.FSM() as fsm:
            fsm_status_reg(platform, m, fsm)
            if self.debug:
                ...
                #fsm_probe(m, fsm)

            with Process(m, "VSYNC_START", to="VBP") as p:
                send_short_packet(p, DsiShortPacketDataType.V_SYNC_START)

            v_porch("VBP", "LINE_START", self.vbp, skip_first_hsync=True)

            with Process(m, "LINE_START", to="LINE_DATA") as p:
                end_of_transmission(p)
                p += m.If(gearbox.output.valid)
                m.d.comb += trig.eq(1)
                send_short_packet(p, DsiShortPacketDataType.H_SYNC_START)
                blanking(p, self.hbp)
                send_short_packet(p, DsiLongPacketDataType.PACKED_PIXEL_STREAM_24_BIT_RGB_8_8_8, self.image_width)
            with m.State("LINE_DATA"):
                with m.If(gearbox.output.line_last & gearbox.output.valid & gearbox.output.ready):
                    m.next = "LINE_END"
                    m.d.sync += frame_last.eq(gearbox.output.frame_last)
                with m.If(~gearbox.output.valid):
                    m.d.sync += self.gearbox_not_ready.eq(self.gearbox_not_ready + 1)
                m.d.comb += self.output.connect_upstream(gearbox.output, allow_partial=True)
            with Process(m, "LINE_END", to=None) as p:
                p += process_write_to_stream(m, self.output, payload=0x0)  # TODO: handle the non 2 lane case
                blanking(p, self.hfp, omit_footer=True)  # we omit the footer to be able to do dispatch the next state with zero cycle delay
                with process_write_to_stream(m, self.output, payload=0x0):
                    with m.If(frame_last):
                        m.next = "VFP"
                    with m.Else():
                        m.next = "LINE_START"

            v_porch("VFP", "FRAME_END", self.vfp)

            with Process(m, "FRAME_END", to="VSYNC_START") as p:
                end_of_transmission(p)


        return m
