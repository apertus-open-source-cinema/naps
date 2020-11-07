from typing import Union

from nmigen import *

from util.bundle import Bundle, UPWARDS, DOWNWARDS


class Stream(Bundle):
    @staticmethod
    def like(model, name=None):
        return Stream(model.payload.shape(), has_last=hasattr(model, "last"), name=name)

    def __init__(self, payload_shape: Union[Shape, int], has_last=False, name=None):
        super().__init__(name=name)

        self.ready = Signal() @ UPWARDS

        self.payload = Signal(payload_shape) @ DOWNWARDS
        self.valid = Signal() @ DOWNWARDS
        if has_last:
            self.last = Signal() @ DOWNWARDS

