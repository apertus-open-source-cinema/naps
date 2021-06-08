from nmigen import *
from naps.cores.video import ImageStream
from .. import PacketHeader
from .aligner import CsiWordAligner

__all__ = ["CsiPacketLayer"]


class CsiPacketLayer(Elaboratable):
    def __init__(self, lane_word_aligner: CsiWordAligner):
        self.lane_word_aligner = lane_word_aligner

        self.output = ImageStream(32)  # we currently only support raw8 with 4 pixels / cycle

    def elaborate(self, platform):
        m = Module()

        packet_ctr = Signal(16)
        with m.FSM():
            with m.State("IDLE"):
                with m.If(self.lane_word_aligner.maybe_first_packet_byte):
                    packet_header = PacketHeader(self.lane_word_aligner.output)
                    with m.If(packet_header.is_packet_valid()):
                        m.d.comb += self.lane_word_aligner.in_packet.eq(1)
                        with m.If(packet_header.data_id.is_long_packet()):
                            m.next = "LONG_PACKET"
                            m.d.sync += packet_ctr.eq(packet_header.word_count)

            with m.State("LONG_PACKET"):
                m.d.comb += self.lane_word_aligner.in_packet.eq(1)
                with m.If(packet_ctr > 4):  # we always process 4 words per cycle
                    m.d.sync += packet_ctr.eq(packet_ctr - 4)
                with m.Else():
                    m.d.sync += packet_ctr.eq(0)
                    m.next = "IDLE"
                    # TODO: steal crc from https://gitlab.com/harmoninstruments/harmon-instruments-open-hdl/-/blob/master/Ethernet/CRC.py
                    # think about how to extract the packet footer

        return m
