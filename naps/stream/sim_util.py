from typing import Iterable
from naps.util.sim import wait_for, do_nothing
from amaranth.lib.stream import Interface as StreamInterface

__all__ = ["write_to_stream", "read_from_stream", "read_packet_from_stream", "write_packet_to_stream"]


def write_to_stream(stream: StreamInterface, payload, timeout=100):
    yield stream.p.eq(payload)
    yield stream.valid.eq(1)
    yield from wait_for(stream.ready, timeout)
    yield stream.valid.eq(0)


def read_from_stream(stream: StreamInterface, timeout=100):
    yield stream.ready.eq(1)
    yield from wait_for(stream.valid, timeout)
    read = yield stream.payload
    yield stream.ready.eq(0)
    return read


def write_packet_to_stream(stream, payload_array, timeout=100):
    for i, p in enumerate(payload_array):
        if i < (len(payload_array) - 1):
            yield from write_to_stream(stream, timeout=timeout, payload=stream.p.shape().const({"p": p, "last": 0}))
        else:
            yield from write_to_stream(stream, timeout=timeout, payload=stream.p.shape().const({"p": p, "last": 1}))


def read_packet_from_stream(stream, timeout=100, allow_pause=True, pause_after_word=0):
    packet = []
    first = True
    while True:
        yield from read_from_stream(stream, timeout=timeout if (first or allow_pause) else 1)
        # TODO(robin): change this when we use the new simulator api again
        payload = yield stream.p.p
        last = yield stream.p.last
        yield from do_nothing(pause_after_word)
        first = False
        packet.append(payload)
        if last:
            return packet
