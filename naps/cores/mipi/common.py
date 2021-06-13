from functools import reduce

from nmigen import *
from naps import packed_struct

__all__ = ["DataIdentifier", "calculate_ecc", "PacketHeader"]


@packed_struct
class DataIdentifier:
    data_type: unsigned(6)
    virtual_channel_identifier: unsigned(2)

    def is_long_packet(self):
        return self.data_type <= 0x0F


def calculate_ecc(header):
    ecc_table = reversed([
        [],
        [],
        [                                        10, 11, 12, 13, 14, 15, 16, 17, 18, 19,     21, 22, 23],
        [                4,  5,  6,  7,  8,  9,                          16, 17, 18, 19, 20,     22, 23],
        [1,      2,  3,              7,  8,  9,              13, 14, 15,             19, 20, 21,     23],
        [0,      2,  3,      5,  6,          9,      11, 12,         15,         18,     20, 21, 22    ],
        [0,  1,      3,  4,      6,      8,      10,     12,     14,         17,         20, 21, 22, 23],
        [0,  1,  2,      4,  5,      7,          10, 11,     13,         16,             20, 21, 22, 23]
    ])
    return Cat(reduce(lambda a, b: a ^ b, (header[i] for i in row), 0) for row in ecc_table)



@packed_struct
class PacketHeader:
    data_id: DataIdentifier
    word_count: unsigned(16)
    ecc: unsigned(8)

    def calculate_ecc(self):
        return calculate_ecc(self.as_value())

    def is_packet_valid(self):
        # one could also recover bit errors using the ecc; maybe do this here
        return self.calculate_ecc() == self.ecc
