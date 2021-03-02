from abc import ABC

from .fatbitstream import FatbitstreamContext
from .hooks import csr_and_driver_method_hook, address_assignment_hook, peripherals_collect_hook
from .pydriver.generate import pydriver_hook
from .tracing_elaborate import fragment_get_with_elaboratable_trace

__all__ = ["SocPlatform"]


class SocPlatform(ABC):
    base_address = None
    _wrapped_platform = None

    # we build a new type that combines the soc and the real platform class
    def __new__(cls, platform, *args, **kwargs):
        return super(SocPlatform, cls).__new__(type(cls.__name__, (cls, platform.__class__), vars(platform)))

    # we pass through all platform methods, because we pretend to be a platform
    def __getattr__(self, item):
        return getattr(self._wrapped_platform, item)

    def __init__(self, platform):
        self._wrapped_platform = platform

        # inject our prepare method into the platform as a starting point for all our hooks
        self.real_prepare = self._wrapped_platform.prepare
        self._wrapped_platform.prepare = self.prepare

        # inject fatbitstream generation into the platform templates
        # we it this way because command_templates might be a property object that cant be written to directly
        original_command_templates = self._wrapped_platform.command_templates
        self._wrapped_platform.extra_command_templates = []
        self._wrapped_platform.__class__.command_templates = property(lambda plat: [
            *original_command_templates,
            *plat.extra_command_templates
        ])

        # store a reference in the platform that is wrapped to be able to retrieve it during e.g. fatbitstream
        # generation
        self._wrapped_platform._soc_platform = self

        self.prepare_hooks = []
        self.to_inject_subfragments = []
        self.final_to_inject_subfragments = []

        self.prepare_hooks.append(csr_and_driver_method_hook)
        self.prepare_hooks.append(address_assignment_hook)
        self.prepare_hooks.append(peripherals_collect_hook)
        self.prepare_hooks.append(pydriver_hook)

    # we override the prepare method of the real platform to be able to inject stuff into the design
    def prepare(self, elaboratable, name="top", *args, **kwargs):
        print("# ELABORATING MAIN DESIGN")
        top_fragment, sames = fragment_get_with_elaboratable_trace(elaboratable, self)

        def inject_subfragments(top_fragment, sames, to_inject_subfragments):
            for elaboratable, name in to_inject_subfragments:
                fragment, fragment_sames = fragment_get_with_elaboratable_trace(elaboratable, self, sames)
                print("<- injecting fragment '{}'".format(name))
                top_fragment.add_subfragment(fragment, name)
            self.to_inject_subfragments = []

        print("\n# ELABORATING SOC PLATFORM ADDITIONS")
        inject_subfragments(top_fragment, sames, self.to_inject_subfragments)
        for hook in self.prepare_hooks:
            print("-> running {}".format(hook.__name__))
            hook(self, top_fragment, sames)
            inject_subfragments(top_fragment, sames, self.to_inject_subfragments)

        print("\ninjecting final fragments")
        inject_subfragments(top_fragment, sames, self.final_to_inject_subfragments)

        print("\ninjecting fatbitstream generation code")
        fc = FatbitstreamContext.get(self)
        self._wrapped_platform.extra_command_templates.extend(fc.generate_fatbitstream_generator(name))

        print("\n\nexiting soc code\n")

        return self.real_prepare(top_fragment, name, *args, **kwargs)
