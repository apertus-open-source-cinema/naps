from lib.bus.stream.stream import Stream
from util.sim import wait_for


def write_to_stream(stream: Stream, **kwargs):
    for k, v in kwargs.items():
        yield getattr(stream, k).eq(v)
    yield stream.valid.eq(1)
    yield from wait_for(stream.ready)
    yield stream.valid.eq(0)


def read_from_stream(stream: Stream):
    yield stream.ready.eq(1)
    yield from wait_for(stream.valid)
    read = (yield stream.payload)
    yield stream.ready.eq(0)
    return read
