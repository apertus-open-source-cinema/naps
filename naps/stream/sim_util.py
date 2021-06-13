from typing import Iterable

from . import Stream, PacketizedStream
from naps.util.sim import wait_for, do_nothing

__all__ = ["write_to_stream", "read_from_stream", "read_packet_from_stream", "write_packet_to_stream"]


def write_to_stream(stream: Stream, timeout=100, **kwargs):
    for k, v in kwargs.items():
        yield stream[k].eq(v)
    yield stream.valid.eq(1)
    yield from wait_for(stream.ready, timeout)
    yield stream.valid.eq(0)


def read_from_stream(stream: Stream, extract="payload", timeout=100):
    yield stream.ready.eq(1)
    yield from wait_for(stream.valid, timeout)
    if isinstance(extract, str):
        read = (yield stream[extract])
    elif isinstance(extract, Iterable):
        read = []
        for x in extract:
            read.append((yield stream[x]))
        read = tuple(read)
    else:
        raise TypeError("extract must be either a string or an iterable of strings")

    yield stream.ready.eq(0)
    return read


def write_packet_to_stream(stream: PacketizedStream, payload_array, timeout=100):
    for i, p in enumerate(payload_array):
        if i < (len(payload_array) - 1):
            yield from write_to_stream(stream, timeout, payload=p, last=0)
        else:
            yield from write_to_stream(stream, timeout, payload=p, last=1)


def read_packet_from_stream(stream: PacketizedStream, timeout=100, allow_pause=True, pause_after_word=0):
    packet = []
    first = True
    while True:
        payload, last = yield from read_from_stream(stream, extract=("payload", "last"), timeout=timeout if (first or allow_pause) else 1)
        yield from do_nothing(pause_after_word)
        first = False
        packet.append(payload)
        if last:
            return packet
