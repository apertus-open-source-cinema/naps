from abc import ABC, abstractmethod
from typing import Callable

from nmigen import *
from nmigen_soc.memory import MemoryMap

from soc import Response
from soc.hooks import csr_hook, address_assignment_hook
from soc.tracing_elaborate import fragment_get_with_elaboratable_trace


class SocPlatform(ABC):
    def __init__(self, platform):
        self.platform = platform

        # we inject our prepare method into the platform
        if self.platform:
            self.real_prepare = self.platform.prepare
            self.platform.prepare = self.prepare

        self.prepare_hooks = []
        self.to_inject_subfragments = []
        self.final_to_inject_subfragments = []

        self.prepare_hooks.append(csr_hook)
        self.prepare_hooks.append(address_assignment_hook)

    # we pass through all platform methods, because we pretend to be one
    def __getattr__(self, item):
        return getattr(self.platform, item)

    # we override the prepare method of the real platform to be able to inject stuff into the design
    def prepare(self, elaboratable, *args, **kwargs):
        print("# ELABORATING MAIN DESIGN")
        top_fragment, sames = fragment_get_with_elaboratable_trace(elaboratable, self)

        def inject_subfragments(top_fragment, sames, to_inject_subfragments):
            for elaboratable, name in to_inject_subfragments:
                fragment, fragment_sames = fragment_get_with_elaboratable_trace(elaboratable, self, sames)
                top_fragment.add_subfragment(Fragment.get(fragment, self), name)
            self.to_inject_subfragments = []

        print("\n# ELABORATING SOC PLATFORM ADDITIONS")
        inject_subfragments(top_fragment, sames, self.to_inject_subfragments)
        for hook in self.prepare_hooks:
            print("\nrunning {}".format(hook.__name__))
            hook(self, top_fragment, sames)
            inject_subfragments(top_fragment, sames, self.to_inject_subfragments)

        print("\ninjecting final fragments")
        inject_subfragments(top_fragment, sames, self.final_to_inject_subfragments)

        return self.real_prepare(top_fragment, *args, **kwargs)

    @abstractmethod
    def BusSlave(self, handle_read: Callable[[Module, Signal, Signal, Callable[[Response], None]], None], handle_write: Callable[[Module, Signal, Signal, Callable[[Response], None]], None], *, memorymap: MemoryMap) -> Fragment:
        """
        Gives an abstract slave for the bus of the Soc.
        Give read_done or write_done a nonzero argument to indicate a read_write error.

        :param handle_read: a function with the signature handle_read(addr, data, read_done)
        :param handle_write: a function with the signature handle_write(addr, data, write_done)
        :param memorymap: the MemoryMap of the peripheral
        """
