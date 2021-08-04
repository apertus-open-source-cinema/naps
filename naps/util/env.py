import os


__all__ = ["naps_getenv"]


def naps_getenv(name, default=None):
    return os.getenv("NAPS_" + name, default)
