# generates MIPI DSI packets in software that can then be send out

from nmigen import *
from naps import resolve
from naps.cores.hdmi import parse_modeline, generate_modeline
from naps.cores.mipi.dsi_tx import DsiShortPacketDataType, DsiLongPacketDataType
from naps.cores.mipi import DataIdentifier, calculate_ecc

__all__ = ["packet_header", "short_packet", "long_packet", "assemble"]


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


@long_packet(DsiLongPacketDataType.PACKED_PIXEL_STREAM_24_BIT_RGB_8_8_8)
def color_line(r, g, b, length):
    yield length * 3
    yield from [r, g, b] * length


@long_packet(DsiLongPacketDataType.BLANKING_PACKET_NO_DATA)
def blanking(length):
    yield length * 3
    yield from [0] * length * 3


def full_line(line_length, front_porch, sync_width, back_porch, v_blanking=False):
    if not v_blanking:
        yield from color_line(255, 0, 0, line_length)
    else:
        yield from blanking(line_length)
    yield from blanking(front_porch)
    yield from packet_header(DsiShortPacketDataType.H_SYNC_START)
    yield from blanking(sync_width)
    yield from packet_header(DsiShortPacketDataType.H_SYNC_END)
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
    yield from packet_header(DsiShortPacketDataType.V_SYNC_START)
    for _ in range(modeline.vsync_end - modeline.vsync_start):
        yield from full_line(**line_args, v_blanking=True)
    yield from packet_header(DsiShortPacketDataType.V_SYNC_END)
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
    bytes = assemble(short_packet(DsiShortPacketDataType.DCS_READ_0_PARAMETER, Const(0xDA, 16)))
    print(f"design.rw_console([{', '.join(['0x{:02x}'.format(x) for x in bytes])}])")
