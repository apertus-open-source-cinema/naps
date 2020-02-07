# A small utility class to do arithmetic with not yet known integers

__all__ = ["FutureInt"]

from modules.clocking.GenericOperatorOverloader import GenericOperatorOverloader


def cache(key, value_generator, cache=[]):
    result = lambda: [value for cur_key, value in cache if key == cur_key]
    if len(result()) == 0:
        cache.append((key, value_generator()))
    return result()[0]


class FutureInt(GenericOperatorOverloader):
    def __init__(self, value=None):
        self.value = value

    def __int__(self):
        assert self.value is not None, "Only fulfilled values are __int__()"
        if callable(self.value):
            return self.value()
        elif isinstance(self.value, int):
            return self.value
        elif isinstance(self.value, FutureInt):
            return int(self.value)

    def __eq__(self, other):
        if isinstance(other, FutureInt):
            return self.pseudo_hash() == other.pseudo_hash()
        elif isinstance(other, int):
            try:
                return int(self) == other
            except AssertionError:
                return False

    def __repr__(self):
        return "<FutureInt {} {}>".format(self.value, id(self))

    def generic_operator(self, item, *, args, kwargs):
        def futureIntContent():
            return int(self).__getattribute__(item)(
                *[int(arg) if isinstance(arg, FutureInt) else arg for arg in args],
                **kwargs,
            )

        return FutureInt(cache((self.pseudo_hash(), args, kwargs), lambda: futureIntContent))

    def be(self, value):
        self.value = value
        return value

    def pseudo_hash(self):
        if self.value is None:
            return id(self)
        elif isinstance(self.value, FutureInt):
            return self.value.pseudo_hash()
        elif isinstance(self.value, int):
            return self.value
        else:
            return hash(self.value)
