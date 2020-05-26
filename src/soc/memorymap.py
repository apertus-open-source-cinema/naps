# TODO: add tests (a lot of them)

import re
from dataclasses import dataclass
from math import ceil
from textwrap import indent
from typing import List

from nmigen._unused import MustUse


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
            return self_stop > other_start
        else:
            return other_stop > self_start

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

    def translate(self, other):
        """
        Translate an other address by the current address
        :param other: the address to translate
        :return: the translated address
        """
        assert isinstance(other, Address)
        assert self.bit_offset == 0
        assert other.address * 8 + other.bit_offset + other.bit_len <= self.bit_len
        return Address(self.address + other.address, other.bit_offset, other.bit_len)

    def range(self):
        """
        Return a range(start_byte, end_byte)
        """
        return range(self.address, self.address + ceil((self.bit_offset + self.bit_len) / 8))


@dataclass
class MemoryMapRow:
    name: str
    address: Address
    writable: bool
    obj: object


class MemoryMap(MustUse):
    def __init__(self, place_at=None, parent=None, top=False, bus_word_width=32):
        """
        A memorymap which can store & allocate (hierarchical) address -> resource mappings
        :param place_at: the optional preference of where the memorymap should be located
        :param bus_word_width: the native word width of the underlying bus in bits.
        """
        assert bus_word_width % 8 == 0
        self.bus_word_width = bus_word_width
        self.place_at: Address = place_at

        self.top = top
        self._parent = parent
        self._inlined_offset = None

        self.entries: List[MemoryMapRow] = []
        self.frozen = False

    def __repr__(self):
        return "<Memorymap top={} byte_len={}>".format(self.top, self.byte_len)

    @property
    def top(self):
        return self._MustUse__silence

    @top.setter
    def top(self, val):
        self._MustUse__silence = val

    @property
    def bus_word_width_bytes(self):
        return int(self.bus_word_width / 8)

    @property
    def subranges(self):
        return [row for row in self.entries if isinstance(row.obj, MemoryMap)]

    @property
    def normal_resources(self):
        return [row for row in self.entries if not isinstance(row.obj, MemoryMap)]

    @property
    def own_offset_normal_resources(self):
        own_offset = self.own_offset
        own_offset.bit_len = self.normal_resources_byte_len * 8
        return own_offset

    @property
    def own_offset(self) -> Address:
        if not self.top:
            if self._parent and self._inlined_offset:
                return self._parent.own_offset.translate(self._inlined_offset)
            elif self._parent:
                own_row_candidates = [row for row in self._parent.subranges if row.obj == self]
                assert len(own_row_candidates) == 1
                return self._parent.own_offset.translate(own_row_candidates[0].address)
            else:
                raise ValueError("the location of the memorymap cant be determined. "
                                 "self is not the toplevel memorymap and is not assigned to one")
        else:
            if self.place_at:
                return Address(self.place_at.address, 0, self.byte_len * 8)
            else:
                return Address(0, 0, self.byte_len * 8)

    @property
    def byte_len(self) -> int:
        """
        Calculate the size (based on the resource with the highest address part) of the memorymap
        :return: the size of the memorymap in bytes (aligned to the bus word width)
        """
        if not self.entries:
            return 0
        real_size = max(
            row.address.address + ceil((row.address.bit_offset + row.address.bit_len) / 8)
            for row in self.entries
        )
        # automatically round up to the next word with self.access_with
        return int(ceil(real_size / self.bus_word_width_bytes) * self.bus_word_width_bytes)

    @property
    def normal_resources_byte_len(self):
        """
        Calculate the size (based on the _normal_ resource with the highest address part) of the memorymap
        :return: the size of the memorymap in bytes (aligned to the bus word width)
        """
        if not self.entries:
            return 0
        real_size = max(
            row.address.address + ceil((row.address.bit_offset + row.address.bit_len) / 8)
            for row in self.normal_resources
        )
        # automatically round up to the next word with self.access_with
        return int(ceil(real_size / self.bus_word_width_bytes) * self.bus_word_width_bytes)

    def is_free(self, check_address):
        """
        Check if the provided address is free.
        :param check_address: the address to check.
        :return: A boolean indicating if the address is free
        """
        for row in self.entries:
            if check_address.collides(row.address):
                return False
        return True

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
        assert not self.frozen
        assert not any(row.name == name for row in self.entries)
        assert bits is not None or address is not None
        if address:
            assert ((bits is None) or (
                    address.bit_len is None)) and bits != address.bit_len, "conflicting length information"
        if not address:
            address = Address(self.byte_len, 0, bits, self.bus_word_width)
        elif bits:
            address.bit_len = bits
        assert address.bit_len
        if not self.is_free(address):
            raise ValueError("address {!r} is not free".format(address, bits))
        self.entries.append(MemoryMapRow(name, address, writable, obj))
        return address

    def _added_to(self, parent, inlined_offset=None):
        self._MustUse__used = True
        self.frozen = True
        self._parent = parent
        self._inlined_offset = inlined_offset
        return self

    def allocate_subrange(self, subrange, name=None, place_at=None):
        """
        Add a sub-memorymap to the Memorymap.
        :type subrange: MemoryMap
        :param name: the name of the subrange. If None the subrange be inlined into this memorymap and no hierarchy will be created.
        :param subrange: The subrange to add
        :param place_at: The desired location of the memorymap fragment. Overrides the subranges preference.
        :return: The address where the subrange is placed
        """
        if subrange.byte_len == 0:
            subrange._added_to(None)
            return  # we do not need to do anything with subranges that are empty
        if not place_at:
            place_at = self.place_at
        assert self.place_at is None
        if name is None:  # inline the memorymap
            place_to = Address(self.byte_len, 0, subrange.byte_len * 8)
            for row in subrange._added_to(self, inlined_offset=place_to).entries:
                self.allocate(row.name, row.writable, address=place_to.translate(row.address), obj=row.obj)
            return place_to
        else:  # add the memorymap as a regular resource. this is later interpreted as hierarchical memorymaps
            return self.allocate(name, True, bits=subrange.byte_len * 8, address=place_at, obj=subrange._added_to(self))

    def flatten(self, hierarchy_separator="."):
        to_return = {}
        for row in self.normal_resources:
            to_return[row.name] = row.address
        for row in self.subranges:
            results = row.obj.flatten(hierarchy_separator)
            for key, value in results.items():
                to_return["{}{}{}".format(row.name, hierarchy_separator, key)] = row.address.translate(value)
        if self.top:
            return {k: self.own_offset.translate(v) for k, v in to_return.items()}
        else:
            return to_return

    @property
    def flat(self):
        return self.flatten()
