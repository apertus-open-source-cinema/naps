from typing import Union

from nmigen import *

from util.interface import Interface, down, up


class Stream(Interface):
    @staticmethod
    def like(model, name=None):
        return Stream(model.payload.shape(), has_last=hasattr(model, "last"), name=name)

    def __init__(self, payload_shape: Union[Shape, int], has_last=False, name=None):
        super().__init__(name=name)

        self.payload = down(Signal(payload_shape))
        self.valid = down(Signal())
        if has_last:
            self.last = down(Signal())

        self.ready = up(Signal())
