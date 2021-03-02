from nmigen import Signal
from naps import BasicStream, DOWNWARDS

__all__ = ["ImageStream"]


class ImageStream(BasicStream):
    """
    A stream that can be used to transfer image data.
    """

    def __init__(self, payload_shape, name=None, src_loc_at=1):
        super().__init__(payload_shape, name, src_loc_at=1 + src_loc_at)
        self.line_last = Signal() @ DOWNWARDS
        self.frame_last = Signal() @ DOWNWARDS
