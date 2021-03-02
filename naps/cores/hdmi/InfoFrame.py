# TODO: this is the beginning of a full hdmi implementation. Finish this.

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class BitVec:
    def __init__(self, len):
        pass


class PacketConstructable(ABC):
    @abstractmethod
    def lower(self):
        raise NotImplementedError()


@dataclass
class DataIslandPacket(PacketConstructable, ABC):
    header_bytes: list
    data_bytes: list


class RgbOrYcbcr(Enum):
    RGB = 0b00
    YCBCR422 = 0b01
    YCBCR444 = 0b10


class ActiveFormatInformationPresent(Enum):
    NO_DATA = 0
    INFORMATION_VALID = 1


class BarInfo(Enum):
    NOT_VALID = 0b00
    VERTICAL_BAR_INFO_VALID = 0b01
    HORIZONTAL_BAR_INFO_VALID = 0b10
    BOTH_VALID = 0b11


class ScanInformation(Enum):
    NO_DATA = 0b00
    OVERSCANNED = 0b01
    UNDERSCANNED = 0b10


class Colorimetry(Enum):
    NO_DADA = 0b00
    SMPTE170_OR_ITU601 = 0b01
    ITU709 = 0b10
    EXTENDED = 0b11


class PictureAspectRatio(Enum):
    NO_DATA = 0b00
    ASPECT_4_3 = 0b01
    ASPECT_16_9 = 0b10


class ActiveFormatAspectRatio(Enum):
    SAME_AS_PICTURE_ASPECT = 0b1000


class ItContent(Enum):
    NO_DATA = 0
    IT_CONTENT = 1


class ExtendedColorimetry(Enum):
    XVYCC601 = 0b000
    XVYCC709 = 0b001


class RgbQuantizationRange(Enum):
    DEFAULT = 0b00
    LIMITED = 0b01
    FULL = 0b10


class NonUniformPictureScaling(Enum):
    NO_KNOWN = 0b00
    HORIZONTAL = 0b01
    VERTICAL = 0b10
    BOTH = 0b11


class VideoIdentificationCode(Enum):
    NO_INFORMATION = 0
    VID_1920_1080_60p = 16
    VID_1920_1080_30p = 34
    VID_1920_1080_25p = 33
    VID_1920_1080_24p = 32
    VID_1920_1080_50p = 31

@dataclass
class AviInfoFrame(PacketConstructable):
    # header
    packet_type = 0x82
    info_frame_version = 0x02
    info_frame_lengh = 0x0D

    # bady
    scan_information: ScanInformation
    rgb_or_ycbcr: RgbOrYcbcr
    active_format_information_present: ActiveFormatInformationPresent
    bar_info: BarInfo
    colorimetry: Colorimetry
    picture_aspect_ratio: PictureAspectRatio


    def lower(self):
        return DataIslandPacket(
            header_bytes=[self.packet_type, self.info_frame_version, self.info_frame_lengh]
        )
