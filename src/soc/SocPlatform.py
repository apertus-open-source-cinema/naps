from abc import ABC, abstractmethod
from typing import Callable

from nmigen import *
from nmigen_soc.memory import MemoryMap

from soc import Response
from soc.util import fragment_get_with_elaboratable_trace, find_elaboratable_sames


class SocPlatform(ABC):
    def __init__(self, platform):
        self.platform = platform

        # we inject our prepare method into the platform
        if self.platform:
            self.real_prepare = self.platform.prepare
            self.platform.prepare = self.prepare

        self.prepare_hooks = []
        self.to_inject_subfragments = []

        def inject_subfragments_prepare_hook(top_fragment, sames):
            for fragment, name in self.to_inject_subfragments:
                top_fragment.add_subfragment(Fragment.get(fragment, self), name)
        self.prepare_hooks.append(inject_subfragments_prepare_hook)

    def inject_subfragment(self, fragment, name=None):
        self.to_inject_subfragments.append((fragment, name))

    # we pass through all platform methods, because we pretend to be one
    def __getattr__(self, item):
        return getattr(self.platform, item)

    # we override the prepare method of the real platform to be able to inject stuff into the design
    def prepare(self, elaboratable, *args, **kwargs):
        top_fragment, elab_trace = fragment_get_with_elaboratable_trace(elaboratable, self)
        sames = find_elaboratable_sames(elab_trace)

        for hook in self.prepare_hooks:
            hook(top_fragment, sames)

        return self.real_prepare(top_fragment, *args, **kwargs)

    @abstractmethod
    def BusSlave(self, handle_read: Callable[[Module, Signal, Signal, Callable[[Response], None]], None], handle_write: Callable[[Module, Signal, Signal, Callable[[Response], None]], None], *, memorymap: MemoryMap):
        """
        Gives an abstract slave for the bus of the Soc.
        Give read_done or write_done a nonzero argument to indicate a read_write error.

        :param handle_read: a function with the signature handle_read(addr, data, read_done)
        :param handle_write: a function with the signature handle_write(addr, data, write_done)
        :param memorymap: the MemoryMap of the peripheral
        """

    @abstractmethod
    def MemoryMap(self) -> MemoryMap:
        """
        Returns an empty MemoryMap object with the right bus properties
        """

