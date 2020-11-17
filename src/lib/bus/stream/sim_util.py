from collections import Iterable

from lib.bus.stream.stream import Stream
from util.sim import wait_for


def write_to_stream(stream: Stream, timeout=100, **kwargs):
    for k, v in kwargs.items():
        yield getattr(stream, k).eq(v)
    yield stream.valid.eq(1)
    yield from wait_for(stream.ready, timeout)
    yield stream.valid.eq(0)


def read_from_stream(stream: Stream, extract="payload", timeout=100):
    yield stream.ready.eq(1)
    yield from wait_for(stream.valid, timeout)
    if isinstance(extract, str):
        read = (yield getattr(stream, extract))
    elif isinstance(extract, Iterable):
        read = []
        for x in extract:
            read.append((yield getattr(stream, x)))
        read = tuple(read)
    else:
        raise TypeError("extract must be either a string or an iterable of strings")

    yield stream.ready.eq(0)
    return read
