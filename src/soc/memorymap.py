# TODO: add tests (a lot of them)

import re
from math import ceil


class Address:
    @staticmethod
    def parse(obj, access_length=4):
        if isinstance(obj, Address):
            return obj
        elif isinstance(obj, str):
            addr, start_bit, stop_bit = [
                int(s, 0) if s else None for s in
                re.match("(0x[0-9a-fA-F]+):?(\\d+)?-?(\\d+)?", obj).groups()
            ]
            if (start_bit is not None) and (stop_bit is not None):
                return Address(addr, start_bit, stop_bit - start_bit)
            elif start_bit is not None:
                return Address(addr, start_bit, 1)
            else:
                return Address(addr, 0, 8 * access_length)
        elif obj is None:
            return None
        else:
            raise ValueError("constructing addresses from type {!r} is not supported".format(type(obj)))

    def __init__(self, address, bit_offset, bit_len=None, access_width=4):
        self.access_width = access_width

        assert bit_offset <= 8 * access_width
        self.bit_offset = bit_offset

        assert address % access_width == 0
        self.address = address

        self.bit_len = bit_len

    def __repr__(self):
        if self.bit_len:
            return "0x{:02X}[{}:{}]".format(self.address, self.bit_offset, self.bit_offset + self.bit_len)
        else:
            return "0x{:02X}[{}:]".format(self.address, self.bit_offset)

    def collides(self, other_address):
        if (self.bit_len is None) or (other_address.bit_len is None):
            raise ValueError("collision detection is impossible with addresses that dont have a length specified")
        # we do all calculations in bits, to ease the checks
        self_start = self.address * 8
        self_stop = self_start + self.bit_len

        other_start = other_address.address * 8
        other_stop = other_start + other_address.bit_len

        if self_start >= other_start:
            return self_stop <= other_start
        else:
            return other_stop <= self_start

    def bits_of_word(self, word_address):
        """
        If the Address is part of the adressed word it returns a tuple of the range of own addressed bits and of the
        bits of the word. otherwise it returns None.
        :param word_address: the address of the word
        :returns a tuple of (word_range, signal_range)
        """
        word = Address(word_address, 0, self.access_width * 8)
        if word.collides(self):
            address_shift = word_address - self.address
            if address_shift == 0:  # we are in the start byte
                length = max(self.bit_len - self.bit_offset, word.bit_len - self.bit_offset)
                word_range = range(self.bit_offset, length)
                signal_range = range(0, length)
            else:  # we are in some subsequent byte
                length = max((self.bit_len + self.bit_offset) - 8 * self.access_width, 8 * self.access_width)
                word_range = range(0, length)
                signal_start = address_shift * 8 - self.bit_offset
                signal_range = range(signal_start, signal_start + length)
            return word_range, signal_range
        else:
            return None


class MemoryMap:
    def __init__(self, name, place_at=None, access_width=4):
        self.name = name
        self.access_width = access_width
        self.place_at = place_at

        self.entries = {}  # name: (address, writable, for_signal)

    def is_free(self, check_address):
        for address, writable, for_signal in self.entries:
            if check_address.collides(address):
                return False
        return True

    def size(self) -> int:
        real_size = max(
            address.address + ceil((address.bit_offset + address.bit_len) / 8)
            for address, writable in self.entries
        )
        # automatically round up to the next word with self.access_with
        return int(ceil(real_size / self.access_width) * self.access_width)

    def allocate(self, name, writable, bits=None, address=None, obj=None):
        assert name not in self.entries
        assert bits or address
        if not address:
            address = Address(self.size() + 1, 0, bits, self.access_width)
        elif bits:
            address.bit_len = bits
        assert address.bit_len
        if not self.is_free(address):
            raise ValueError("address {!r} with length {}bits is not free".format(address, bits))
        self.entries[name] = (address, writable, obj)
        return address

    def allocate_subrange(self, subrange, place_at=None):
        """ Add a sub-memorymap to the Memorymap.
        :type subrange: MemoryMap
        :param subrange: The subrange to add
        :param place_at: The desired location of the memorymap fragment. Overrides the subranges preference.
        :return: The address where the subrange is placed
        """
        if not place_at:
            place_at = self.place_at
        return self.allocate(subrange.name, True, bits=subrange.size() * 8, address=place_at, obj=subrange)
