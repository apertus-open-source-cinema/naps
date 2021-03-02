
__all__ = ["EncodingSpace"]


class EncodingSpace:
    @property
    def numeric_range(self):
        raise NotImplementedError()
