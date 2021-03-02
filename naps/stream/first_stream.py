from nmigen import *
from ..data_structure import DOWNWARDS
from .stream import BasicStream

__all__ = ["PacketizedFirstStream"]


class PacketizedFirstStream(BasicStream):
    """
    A stream that carries a payload and can separate Packets via a first signal that is asserted on the
    first word of a packet
    """

    def __init__(self, payload_shape, name=None, src_loc_at=1):
        super().__init__(payload_shape, name, src_loc_at=1 + src_loc_at)
        self.first = Signal() @ DOWNWARDS
