# A small utility class to do arithmetic with not yet known integers

__all__ = ["LazyInt"]


def __init__(self, value=None):
    self.value = value


def __int__(self):
    assert self.value is not None, "Only fulfilled values are __int__()"
    if callable(self.value):
        return self.value()
    elif isinstance(self.value, int):
        return self.value


def fulfil(self, value):
    self.value = value
    return value


def generate_method_wrapper(method):
    return lambda self, *args, **kwargs: LazyInt(lambda: int(self).__getattribute__(method)(*args, **kwargs))


LazyInt = type("LazyInt", (object,), {
    "__init__": __init__,
    "__int__": __int__,
    "fulfil": fulfil,
    **{k: generate_method_wrapper(k) for k in dir(int) if k not in [*dir(object), "__int__"]}
})
