from enum import IntEnum

__all__ = ["CsiShortPacketDataType", "CsiLongPacketDataType"]


class CsiShortPacketDataType(IntEnum):
    FRAME_START = 0x00
    FRAME_END = 0x01
    LINE_START = 0x02
    LINE_END = 0x03


class CsiLongPacketDataType(IntEnum):
    RAW6 = 0x28
    RAW7 = 0x29
    RAW8 = 0x2A
    RAW10 = 0x2B
    RAW12 = 0x2C
    RAW14 = 0x2D