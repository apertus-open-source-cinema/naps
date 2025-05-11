from abc import ABC

from amaranth import Fragment

from .hooks import csr_and_driver_item_hook, address_assignment_hook, peripherals_collect_hook
from .pydriver.generate import pydriver_hook

__all__ = ["SocPlatform", "soc_platform_name", "PERIPHERAL_DOMAIN"]

PERIPHERAL_DOMAIN = "peripheral_domain"

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
        platform._soc_platform = self

        self._wrapped_platform = platform

        self.prepare_hooks = []
        self.to_inject_subfragments = []
        self.final_to_inject_subfragments = []

        self.prepare_hooks.append(csr_and_driver_item_hook)
        self.prepare_hooks.append(address_assignment_hook)
        self.prepare_hooks.append(peripherals_collect_hook)
        self.prepare_hooks.append(pydriver_hook)

    # we override the prepare method of the real platform to be able to inject stuff into the design
    def prepare_soc(self, elaboratable):
        print("# ELABORATING MAIN DESIGN")
        top_fragment = Fragment.get(elaboratable, self)

        def inject_subfragments(top_fragment, to_inject_subfragments):
            for elaboratable, name in to_inject_subfragments:
                fragment = Fragment.get(elaboratable, self)
                print("<- injecting fragment '{}'".format(name))
                top_fragment.add_subfragment(fragment, name)
            self.to_inject_subfragments = []

        print("\n# ELABORATING SOC PLATFORM ADDITIONS")
        inject_subfragments(top_fragment, self.to_inject_subfragments)
        for hook in self.prepare_hooks:
            print("-> running {}".format(hook.__name__))
            hook(self, top_fragment)
            inject_subfragments(top_fragment, self.to_inject_subfragments)

        print("\ninjecting final fragments")
        inject_subfragments(top_fragment, self.final_to_inject_subfragments)

        return top_fragment


def soc_platform_name(obj):
    if obj is None:
        return "None"
    else:
        if not isinstance(obj, type):
            obj = obj.__class__
        return obj.__name__.replace("SocPlatform", "")
