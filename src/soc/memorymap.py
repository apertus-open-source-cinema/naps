# TODO: add tests (a lot of them)

import re
from math import ceil


class Address:
    @staticmethod
    def parse(obj, bus_word_width=32):
        """
        Parse an address object from either a string or pass an address object or none through.
        :param obj: either a string in the format 0xABCD[optional_python:slice] or an Address object or None
        :param bus_word_width: the native word width of the underlying bus in bits.
        :return: an address object or None
        """
        if isinstance(obj, Address):
            return obj
        elif isinstance(obj, str):
            addr, start_bit, stop_bit = [
                int(s, 0) if s else None for s in
                re.match("(0x[0-9a-fA-F]+)\\[?(\\d+)?:?(\\d+)?\\]?", obj).groups()
            ]
            if (start_bit is not None) and (stop_bit is not None):
                return Address(addr, start_bit, stop_bit - start_bit)
            elif start_bit is not None:
                return Address(addr, start_bit, 1)
            else:
                return Address(addr, 0, bus_word_width)
        elif obj is None:
            return None
        else:
            raise ValueError("constructing addresses from type {!r} is not supported".format(type(obj)))

    def __init__(self, address, bit_offset, bit_len=None, bus_word_width=32):
        """
        An address type, that can either represent only a base adress or a base adress and a length.
        :param address: the base address in bytes
        :param bit_offset: the offset of the start of the address unit in bits relative to the start byte. must be positive.
        :param bit_len: the length of the address unit in bits.
        :param bus_word_width: the native word width of the underlying bus in bits.
        """
        assert bus_word_width % 8 == 0
        self.bus_word_width = bus_word_width

        assert bit_offset <= bus_word_width
        self.bit_offset = bit_offset

        assert address % int(bus_word_width / 8) == 0
        self.address = address

        self.bit_len = bit_len

    def __repr__(self):
        if self.bit_len is not None:
            return "0x{:02X}[{}:{}]".format(self.address, self.bit_offset, self.bit_offset + self.bit_len)
        else:
            return "0x{:02X}[{}:]".format(self.address, self.bit_offset)

    def collides(self, other_address):
        if (self.bit_len is None) or (other_address.bit_len is None):
            raise ValueError("collision detection is impossible with addresses that dont have a length specified")
        self_start = self.address * 8
        self_stop = self_start + self.bit_len

        other_start = other_address.address * 8
        other_stop = other_start + other_address.bit_len

        if self_start <= other_start:
            return self_stop <= other_start
        else:
            return other_stop <= self_start

    def bits_of_word(self, word_address: int):
        """
        If the Address is part of the addressed word it returns a tuple of the range of own addressed bits and of the
        bits of the word. otherwise it returns None.
        :param word_address: the base address of the word. this is not an Address object but rather an int because we
        need only the base address.
        :return a tuple of (word_range, signal_range)
        """
        word = Address(word_address, 0, self.bus_word_width)
        if word.collides(self):
            address_shift = word_address - self.address
            if address_shift == 0:  # we are in the start word
                stop = max(self.bit_len - self.bit_offset, word.bit_len - self.bit_offset)
                word_range = range(self.bit_offset, stop)
                signal_range = range(0, stop)
            else:  # we are in some subsequent word
                stop = max((self.bit_len + self.bit_offset) - self.bus_word_width, self.bus_word_width)
                word_range = range(0, stop)
                signal_start = address_shift * 8 - self.bit_offset
                signal_range = range(signal_start, signal_start + stop)
            return word_range, signal_range
        else:
            return None


class MemoryMap:
    def __init__(self, name, place_at=None, bus_word_width=32):
        """
        A memorymap which can store & allocate (hierarchical) address -> resource mappings
        :param name: the name of the memorymap (segment)
        :param place_at: the optional preference of where the memorymap should be located
        :param bus_word_width: the native word width of the underlying bus in bits.
        """
        self.name = name
        assert bus_word_width % 8 == 0
        self.bus_word_width = bus_word_width
        self.place_at = place_at

        self.entries = {}  # name: (address, writable, for_signal)

    def is_free(self, check_address):
        """
        Check if the provided address is free.
        :param check_address: the address to check.
        :return: A boolean indicating if the address is free
        """
        for address, writable, for_signal in self.entries:
            if check_address.collides(address):
                return False
        return True

    def size(self) -> int:
        """
        Calculate the size (based on the resource with the highest address part) of the memorymap
        :return: the size of the memorymap in bytes (aligned to the bus word width)
        """
        real_size = max(
            address.address + ceil((address.bit_offset + address.bit_len) / 8)
            for address, writable in self.entries
        )
        # automatically round up to the next word with self.access_with
        bus_word_width_bytes = int(self.bus_word_width / 8)
        return int(ceil(real_size / bus_word_width_bytes) * bus_word_width_bytes)

    def allocate(self, name, writable, bits=None, address=None, obj=None):
        """
        Allocate / add a resource to the memorymap.
        :param name: the name of the resource
        :param writable: a boolean indicating if the resource is writable
        :param bits: the width of the peripheral
        :param address: the address to place the resource to (optional)
        :param obj: an object to attach to that memory location. In the case of hierarchical memorymaps,
        this is the sub memorymap
        :return: the address of the resource
        """
        assert name not in self.entries
        assert bits or address
        assert ((bits is None) or (address.bit_len is None)) and bits != address.bit_len, "conflicting length information"
        if not address:
            address = Address(self.size() + 1, 0, bits, self.bus_word_width)
        elif bits:
            address.bit_len = bits
        assert address.bit_len
        if not self.is_free(address):
            raise ValueError("address {!r} with length {}bits is not free".format(address, bits))
        self.entries[name] = (address, writable, obj)
        return address

    def allocate_subrange(self, subrange, place_at=None):
        """
        Add a sub-memorymap to the Memorymap.
        :type subrange: MemoryMap
        :param subrange: The subrange to add
        :param place_at: The desired location of the memorymap fragment. Overrides the subranges preference.
        :return: The address where the subrange is placed
        """
        if not place_at:
            place_at = self.place_at
        assert self.place_at is None
        return self.allocate(subrange.name, True, bits=subrange.size() * 8, address=place_at, obj=subrange)
