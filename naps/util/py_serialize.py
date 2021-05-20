# utilities for serializing objects into python code. Useful eg. for pydriver


def is_serializable(obj):
    if type(obj) in (str, int, float, complex, bool, bytes, bytearray, range):
        return True
    elif type(obj) in (list, tuple, set, frozenset):
        return all(is_serializable(x) for x in obj)
    elif type(obj) == dict:
        return all(is_serializable(k) and is_serializable(v) for k, v in obj.items())
    else:
        return False


def serialize(obj):
    assert is_serializable(obj)
    return repr(obj)
