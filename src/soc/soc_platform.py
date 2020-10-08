from abc import ABC

from soc.fatbitstream import FatbitstreamContext
from soc.pydriver.generate import pydriver_hook
from soc.hooks import csr_hook, address_assignment_hook, peripherals_collect_hook
from soc.tracing_elaborate import fragment_get_with_elaboratable_trace


class SocPlatform(ABC):
    base_address = None
    _platform = None

    # we pass through all platform methods, because we pretend to be a platform
    def __getattr__(self, item):
        return getattr(self._platform, item)

    # we also pretend to be the class. a bit evil but works for now
    @property
    def __class__(self):
        return self._platform.__class__

    def __init__(self, platform):
        self._platform = platform

        # inject our prepare method into the platform as a starting point for all our hooks
        self.real_prepare = self._platform.prepare
        self._platform.prepare = self.prepare

        # inject fatbitstream generation into the platforms templates
        # we it this way because command_templates might be a property object that cant be written to directly
        original_command_templates = self._platform.command_templates
        self._platform.extra_command_templates = []
        self._platform.__class__.command_templates = property(lambda plat: [
            *original_command_templates,
            *plat.extra_command_templates
        ])

        self.prepare_hooks = []
        self.to_inject_subfragments = []
        self.final_to_inject_subfragments = []

        self.prepare_hooks.append(csr_hook)
        self.prepare_hooks.append(address_assignment_hook)
        self.prepare_hooks.append(peripherals_collect_hook)
        self.prepare_hooks.append(pydriver_hook)

    # we override the prepare method of the real platform to be able to inject stuff into the design
    def prepare(self, elaboratable, name, *args, **kwargs):
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
        self._platform.extra_command_templates.extend(fc.generate_fatbitstream_generator(name))

        print("\n\nexiting soc code\n")

        return self.real_prepare(top_fragment, name, *args, **kwargs)
