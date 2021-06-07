# generates MIPI DSI packets in software that can then be send out

from enum import Enum, IntEnum
from functools import reduce
from pathlib import Path

from nmigen import *
from tqdm import tqdm

from naps import packed_struct, resolve, parse_modeline, generate_modeline


class DataType(IntEnum):
    pass


class ShortPacketDataType(DataType):
    V_SYNC_START = 0x01
    V_SYNC_END = 0x11
    H_SYNC_START = 0x21
    H_SYNC_END = 0x31
    END_OF_TRANSMISSION_PACKET = 0x08
    COLOR_MODE_OFF = 0x02
    COLOR_MODE_ON = 0x12
    SHUT_DOWN_PERIPHERAL = 0x22
    TURN_ON_PERIPHERAL = 0x32
    GENERIC_SHORT_WRITE_0_PARAMETER = 0x03
    GENERIC_SHORT_WRITE_1_PARAMETER = 0x13
    GENERIC_SHORT_WRITE_2_PARAMETER = 0x23
    GENERIC_READ_0_PARAMETER = 0x04
    GENERIC_READ_1_PARAMETER = 0x14
    GENERIC_READ_2_PARAMETER = 0x24
    DCS_SHORT_WRITE_0_PARAMETER = 0x05
    DCS_SHORT_WRITE_1_PARAMETER = 0x15
    DCS_READ_0_PARAMETER = 0x06
    SET_MAXIMUM_RETURN_PACKET_SIZE = 0x37


class LongPacketDataType(DataType):
    NULL_PACKET_NO_DATA = 0x09
    BLANKING_PACKET_NO_DATA = 0x19
    GENERIC_LONG_WRITE = 0x29
    DCS_LONG_WRITE = 0x39
    LOOSELY_PACKET_PIXEL_STREAM_20_BIT_YCBCR_4_2_2 = 0x0C
    PACKED_PIXEL_STREAM_24_BIT_YCBCR_4_2_2 = 0x1C
    PACKED_PIXEL_STREAM_16_BIT_YCBCR_4_2_2 = 0x2C
    PACKED_PIXEL_STREAM_30_BIT_RGB_10_10_10 = 0x0D
    PACKED_PIXEL_STREAM_36_BIT_RGB_12_12_12 = 0x1D
    PACKED_PIXEL_STREAM_12_BIT_YCBCR_4_2_0 = 0x3D
    PACKED_PIXEL_STREAM_16_BIT_RGB_5_6_5 = 0x0E
    PACKED_PIXEL_STREAM_18_BIT_RGB_6_6_6 = 0x1E
    LOOSELY_PACKET_PIXEL_STREAM_18_BIT_RGB_6_6_6 = 0x2E
    PACKED_PIXEL_STREAM_24_BIT_RGB_8_8_8 = 0x3E


@packed_struct
class DataIdentifier:
    data_type: unsigned(6)
    virtual_channel_identifier: unsigned(2)

    def is_long_packet(self):
        return self.data_type <= 0x0F


@packed_struct
class MipiErrorResponse:
    SOT_ERROR: unsigned(1)
    SOT_SYNC_ERROR: unsigned(1)
    EOT_SYNC_ERROR: unsigned(1)
    ESCAPE_MODE_ENTRY_COMMAND_ERROR: unsigned(1)
    LOW_POWER_TRANSMIT_SYNC_ERROR: unsigned(1)
    PERIPHERAL_TIMEOUT_ERROR: unsigned(1)
    FALSE_CONTROL_ERROR: unsigned(1)
    CONTENTION_DETECTED: unsigned(1)
    ECC_ERROR_SINGLE_BIT_CORRECTED: unsigned(1)
    ECC_ERROR_MULTI_BIT_NOT_CORRECTED: unsigned(1)
    CHECKSUM_ERROR: unsigned(1)
    DSI_DATA_TYPE_NOT_RECOGNIZED: unsigned(1)
    DSI_VC_ID_INVALID: unsigned(1)
    INVALID_TRANSMISSION_LENGTH: unsigned(1)
    RESERVED: unsigned(1)
    DSI_PROTOCOL_VIOLATION: unsigned(1)


def calculate_ecc(bytes):
    ecc_table = reversed([
        [],
        [],
        [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23],
        [4, 5, 6, 7, 8, 9, 16, 17, 18, 19, 20, 22, 23],
        [1, 2, 3, 7, 8, 9, 13, 14, 15, 19, 20, 21, 23],
        [0, 2, 3, 5, 6, 9, 11, 12, 15, 18, 20, 21, 22],
        [0, 1, 3, 4, 6, 8, 10, 12, 14, 17, 20, 21, 22, 23],
        [0, 1, 2, 4, 5, 7, 10, 11, 13, 16, 20, 21, 22, 23]
    ])
    return Cat(reduce(lambda a, b: a ^ b, (bytes[i] for i in row), 0) for row in ecc_table)


def packet_header(data_type, payload=Const(0, 16)):
    to_return = []
    to_return.append(Value.cast(DataIdentifier(virtual_channel_identifier=0, data_type=data_type)))
    to_return.append(payload[0:8])
    to_return.append(payload[8:16])
    to_return.append(calculate_ecc(Cat(*to_return)))
    return to_return


short_packet = packet_header


def long_packet(data_type):
    def inner(f):
        def to_return(*args, **kwargs):
            f_gen = f(*args, **kwargs)
            length = next(f_gen)
            yield from packet_header(data_type, Const(length, 16))
            yield from f_gen
            yield from [Const(0, 8), Const(0, 8)]  # Packet footer without checksum

        return to_return

    return inner


@long_packet(LongPacketDataType.PACKED_PIXEL_STREAM_24_BIT_RGB_8_8_8)
def color_line(r, g, b, length):
    yield length * 3
    yield from [r, g, b] * length


@long_packet(LongPacketDataType.BLANKING_PACKET_NO_DATA)
def blanking(length):
    yield length * 3
    yield from [0] * length * 3


def full_line(line_length, front_porch, sync_width, back_porch, v_blanking=False):
    if not v_blanking:
        yield from color_line(255, 0, 0, line_length)
    else:
        yield from blanking(line_length)
    yield from blanking(front_porch)
    yield from packet_header(ShortPacketDataType.H_SYNC_START)
    yield from blanking(sync_width)
    yield from packet_header(ShortPacketDataType.H_SYNC_END)
    yield from blanking(back_porch)


def full_frame(modeline):
    line_args = dict(
        line_length=modeline.hres,
        front_porch=modeline.hsync_start - modeline.hres,
        sync_width=modeline.hsync_end - modeline.hsync_start,
        back_porch=modeline.hscan - modeline.hsync_end
    )

    yield from [0b10111000] * 2
    for _ in range(modeline.vres):
        yield from full_line(**line_args, v_blanking=False)
    for _ in range(modeline.vsync_start - modeline.vres):
        yield from full_line(**line_args, v_blanking=True)
    yield from packet_header(ShortPacketDataType.V_SYNC_START)
    for _ in range(modeline.vsync_end - modeline.vsync_start):
        yield from full_line(**line_args, v_blanking=True)
    yield from packet_header(ShortPacketDataType.V_SYNC_END)
    for _ in range(modeline.hscan - modeline.vsync_end):
        yield from full_line(**line_args, v_blanking=True)


def assemble(generator):
    bytes = bytearray()
    for byte in generator:
        if not isinstance(byte, int):
            assert len(byte) == 8
            bytes.append(resolve(byte))
        else:
            bytes.append(byte)
    return bytes


if __name__ == "__main__":
    modeline = parse_modeline(generate_modeline(480, 480, 30))
    bytes = assemble(color_line(255, 255, 0, 480))
    print(f"design.rw_console([{', '.join(['0x{:02x}'.format(x) for x in bytes])}])")
