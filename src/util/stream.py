from typing import Union

from nmigen import *
from nmigen._unused import MustUse

from util.bundle import Bundle


class StreamEndpoint(Bundle, MustUse):
    @staticmethod
    def like(other, is_sink=None, name=None):
        return StreamEndpoint(
            payload_shape=other.payload.shape(),
            is_sink=other.is_sink if is_sink is None else is_sink,
            has_last=other.has_last,
            name=name or (other.name + "_$like")
        )

    def __init__(self, payload_shape: Union[Shape, int], is_sink, has_last=False, name=None):
        super().__init__(name=name)

        assert isinstance(is_sink, bool)
        self.is_sink = is_sink

        self.payload = Signal(payload_shape)
        self.valid = Signal()
        self.ready = Signal()
        if has_last:
            self.last = Signal()

    @property
    def has_last(self):
        return hasattr(self, "last")

    def connect(self, source, allow_back_to_back=False):
        sink = self

        if not allow_back_to_back:
            assert sink.is_sink is True
            assert sink._MustUse__used is False
            sink._MustUse__used = True
        assert source._MustUse__used is False
        assert source.is_sink is False
        source._MustUse__used = True

        assert source.has_last == sink.has_last

        stmts = [
            sink.payload.eq(source.payload),
            sink.valid.eq(source.valid),
            source.ready.eq(sink.ready),
        ]
        if hasattr(source, "last"):
            stmts += [sink.last.eq(source.last)]

        return stmts

