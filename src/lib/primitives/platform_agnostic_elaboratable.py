# TODO: rework so that we can define PlatformAgnosticElaboratables in the corresponding vendor directories
from nmigen import *


class PlatformAgnosticElaboratable(Elaboratable):
    """
    An abstract Elaboratable that has a different elaboration path depending on the platform.
    While the definition of the elaboratable is independent of any platform, the elaboration path is dependent on the platform.

    The real implementation should be named elaborateElaboratableName and be a member of the target platform.
    """
    def elaborate(self, platform):
        elaborate_name = "elaborate" + self.__class__.__name__
        if not hasattr(platform, elaborate_name):
            self.fallback_elaborate(platform)

        elaborate_function =  getattr(platform, elaborate_name)
        return elaborate_function(self)

    def fallback_elaborate(self, platform):
        raise NotImplementedError("The platform {!r} does not implement {}(self, elaborate) and therefore cant "
                                  "elaborate a {}".format(platform, "elaborate" + self.__class__.__name__, self.__class__.__name__))