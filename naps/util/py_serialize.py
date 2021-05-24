# utilities for serializing objects into python code. Useful eg. for pydriver

__all__ = ["is_py_serializable", "py_serialize"]


def is_py_serializable(obj):
    if obj is None:
        return True
    if type(obj) in (str, int, float, complex, bool, bytes, bytearray, range):
        return True
    elif type(obj) in (list, tuple, set, frozenset):
        return all(is_py_serializable(x) for x in obj)
    elif type(obj) in (dict,):
        return all(is_py_serializable(k) and is_py_serializable(v) for k, v in obj.items())
    else:
        return False


def py_serialize(obj):
    assert is_py_serializable(obj)
    return repr(obj)
