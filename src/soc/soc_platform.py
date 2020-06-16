from abc import ABC

from nmigen import *
from nmigen.build import Platform

from soc.bus_slave import HandleRead, HandleWrite
from soc.driver.pydriver import pydriver_hook
from soc.hooks import csr_hook, address_assignment_hook
from soc.memorymap import MemoryMap
from soc.tracing_elaborate import fragment_get_with_elaboratable_trace


class SocPlatform(ABC):
    bus_slave_type = None
    base_address = None

    def __init__(self, platform):
        self._platform = platform

        # we inject our prepare method into the platform
        if self._platform:
            self.real_prepare = self._platform.prepare
            self._platform.prepare = self.prepare

        self.prepare_hooks = []
        self.to_inject_subfragments = []
        self.final_to_inject_subfragments = []

        self.prepare_hooks.append(csr_hook)
        self.prepare_hooks.append(address_assignment_hook)
        self.prepare_hooks.append(pydriver_hook)

    # we pass through all platform methods, because we pretend to be one
    def __getattr__(self, item):
        return getattr(self._platform, item)

    # we also pretend to be the class. a bit evil but well...
    @property
    def __class__(self):
        return self._platform.__class__

    # we override the prepare method of the real platform to be able to inject stuff into the design
    def prepare(self, elaboratable, *args, **kwargs):
        print("# ELABORATING MAIN DESIGN")
        top_fragment, sames = fragment_get_with_elaboratable_trace(elaboratable, self)

        def inject_subfragments(top_fragment, sames, to_inject_subfragments):
            for elaboratable, name in to_inject_subfragments:
                fragment, fragment_sames = fragment_get_with_elaboratable_trace(elaboratable, self, sames)
                top_fragment.add_subfragment(fragment, name)
            self.to_inject_subfragments = []

        print("\n# ELABORATING SOC PLATFORM ADDITIONS")
        inject_subfragments(top_fragment, sames, self.to_inject_subfragments)
        for hook in self.prepare_hooks:
            print("\nrunning {}".format(hook.__name__))
            hook(self, top_fragment, sames)
            inject_subfragments(top_fragment, sames, self.to_inject_subfragments)

        print("\ninjecting final fragments")
        inject_subfragments(top_fragment, sames, self.final_to_inject_subfragments)

        print("\n\nexiting soc code\n")

        return self.real_prepare(top_fragment, *args, **kwargs)

    def BusSlave(
        self,
        handle_read: HandleRead,
        handle_write: HandleWrite,
        memorymap: MemoryMap
    ) -> Module:
        """
        Gives an abstract slave for the bus of the Soc.
        Give read_done or write_done a nonzero argument to indicate a read_write error.

        :param handle_read: a function with the signature handle_read(m, addr, data, read_done) that is used to insert logic to the read path.
        :param handle_write: a function with the signature handle_write(m, addr, data, write_done) that is used to insert logic to the write path.
        :param memorymap: the MemoryMap of the peripheral
        """
        assert self.bus_slave_type is not None
        bus_slave = self.bus_slave_type(handle_read, handle_write, memorymap)

        m = Module()  # we will pick this empty module up later in the prepare step. It is just a marker
        m.bus_slave = bus_slave
        return m
