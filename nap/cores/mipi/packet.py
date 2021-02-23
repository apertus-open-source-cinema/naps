from enum import Enum
from functools import reduce
from nmigen import *
from nap import packed_struct, ImageStream
from .aligner import LaneWordAligner


class ShortPacketDataType(Enum):
    FRAME_START = 0x00
    FRAME_END = 0x01
    LINE_START = 0x02
    LINE_END = 0x03


class LongPacketDataType(Enum):
    RAW6 = 0x28
    RAW7 = 0x29
    RAW8 = 0x2A
    RAW10 = 0x2B
    RAW12 = 0x2C
    RAW14 = 0x2D


@packed_struct
class DataIdentifier:
    virtual_channel_identifier = unsigned(2)
    data_type = unsigned(6)

    def is_long_packet(self):
        return self.data_type <= 0x0F


@packed_struct
class PacketHeader:
    data_id: DataIdentifier
    word_count: unsigned(16)
    ecc: unsigned(8)

    def calculate_ecc(self):
        ecc_table = [
            [],
            [],
            [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23],
            [4,  5,  6,  7,  8,  9,  16, 17, 18, 19, 20, 22, 23],
            [1,  2,  3,  7,  8,  9,  13, 14, 15, 19, 20, 21, 23],
            [0,  2,  3,  5,  6,  9,  11, 12, 15, 18, 20, 21, 22],
            [0,  1,  3,  4,  6,  8,  10, 12, 14, 17, 20, 21, 22, 23],
            [0,  1,  2,  4,  5,  7,  10, 11, 13, 16, 20, 21, 22, 23]
        ]
        return Cat(reduce(lambda a, b: a ^ b, (self.as_value()[i] for i in row)) for row in ecc_table)

    def is_packet_valid(self):
        # one could also recover bit errors using the ecc; maybe do this here
        return self.calculate_ecc() == self.ecc


class MipiCSIPacketLayer(Elaboratable):
    def __init__(self, lane_word_aligner: LaneWordAligner):
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
