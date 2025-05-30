from abc import ABCMeta
from glob import glob
from importlib import import_module
from os.path import join, dirname, split

from amaranth import *
from amaranth.vendor import LatticePlatform, XilinxPlatform
from naps import SimPlatform


class ImplementationMarkerMetaclass(ABCMeta):
    @property
    def implementation(self):
        if not hasattr(self, "_marker_type"):
            self._marker_type = type("{}Implementation".format(self.__name__), (), {})
        return self._marker_type


class PlatformAgnosticElaboratable(Elaboratable, metaclass=ImplementationMarkerMetaclass):
    """
    A helper to write Platform agnostic code. Searches in the vendor directories for the real elaboratable.
    """

    @classmethod
    def _search_in_path(cls, path):
        marker_type = cls.implementation
        basepath = __name__.split(".")[:-1] + [path]
        files = [split(p)[-1].replace(".py", "") for p in glob(join(dirname(__file__), path) + "/*.py")]
        for file in files:
            module = import_module(".".join(basepath + [file]))
            for candidate in [getattr(module, k) for k in dir(module)]:
                if isinstance(candidate, type) and issubclass(candidate, marker_type):
                    return candidate
        raise PrimitiveNotSupportedByPlatformError()

    def elaborate(self, platform):
        if isinstance(platform, XilinxPlatform) and platform.family == "series7":
            elaboratable = self._search_in_path("xilinx_s7")
        elif isinstance(platform, LatticePlatform) and platform.family == "machxo2":
            elaboratable = self._search_in_path("lattice_machxo2")
        elif isinstance(platform, LatticePlatform) and platform.family == "ecp5":
            elaboratable = self._search_in_path("lattice_ecp5")
        elif isinstance(platform, SimPlatform):
            return Module()
        else:
            raise PlatformNotSupportedError()

        return elaboratable.elaborate(self, platform)


class PrimitiveNotSupportedByPlatformError(ValueError):
    pass


class PlatformNotSupportedError(ValueError):
    pass
