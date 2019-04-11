from nmigen import *
import re

from util import yosys


class XilinxBlackbox:
    """Wraps the a Xilinx ip as a convenient blackbox.
    """

    def __init__(self):
        self.module = self.module or self.__class__.__name__
        self.ports = yosys.get_module_ports("+/xilinx/cells_xtra.v", self.module)
        self.hierarchy = self._find_hierarchy(list(self.ports.keys()))
        self.signal_proxy = SignalProxy(self.hierarchy, self.ports, path=self.module)

        assert type(self) != "Blackbox", "Do not instantiate `XilinxBlackbox` directly. Use its subclasses!"

    def elaborate(self, platform):
        m = Module()

        named_ports = {
            "{}_{}".format(self.ports[name]["direction"], name): signal
            for name, signal in self.signal_proxy.used_ports().items()
        }
        m.submodules.instance = Instance(self.module, **named_ports)

        return m

    def __getattr__(self, item):
        return self.signal_proxy.__getattr__(item)

    def _find_hierarchy(self, names):
        if isinstance(names, list): names = {v: v for v in sorted(names)}
        if isinstance(names, str): return names

        hierarchy = names.copy()
        for n, signal_name in names.items():
            added = False
            for h_name in reversed(list(hierarchy.keys())):
                common_start = self._common_start(n, h_name)
                match = re.match("([A-Z2]{3,})\d?|(\d)", common_start)

                if match:
                    prefix = match[1] or match[2]
                    strip = lambda s: s.replace(prefix, "")

                    if isinstance(hierarchy[h_name], str):
                        children = {strip(n): signal_name, strip(h_name): hierarchy[h_name]}
                    else:
                        children = {strip(n): signal_name, **{strip(k): v for k, v in hierarchy[h_name].items()}}

                    del hierarchy[h_name]
                    try:
                        del hierarchy[n]
                    except KeyError:
                        pass

                    hierarchy[prefix] = children
                    added = True
                    break
            if not added:
                hierarchy[n] = signal_name

        if "" in list(hierarchy.keys()):
            return list(hierarchy.values())[0]

        return {k: self._find_hierarchy(v) for k, v in hierarchy.items()}

    @staticmethod
    def _common_start(a, b):
        """Returns the characters two strings have in common in the beginning"""
        common_start = ""
        for i in range(min(len(a), len(b))):
            if a[i] == b[i]:
                common_start += a[i]
            else:
                break
        return common_start


class SignalProxy:
    def __init__(self, hierarchy, ports, path="/"):
        self.hierarchy = hierarchy
        self.ports = ports
        self.path = path

        self._used_ports = {}
        self.children = {}

    def used_ports(self):
        child_ports = {}
        for c in self.children.values():
            child_ports = {**child_ports, **c.used_ports()}
        return {**self._used_ports, **child_ports}

    def __getattr__(self, item):
        item = item.upper()

        if item not in self.hierarchy:
            raise KeyError("{} not found in {}".format(item, self.path))
        requested = self.hierarchy[item]
        if isinstance(requested, dict):
            if item not in self.children:
                self.children[item] = SignalProxy(requested, self.ports, path="{}/{}".format(self.path, item))
            return self.children[item]

        # do the real signal finding
        if requested not in self._used_ports:
            self._used_ports[requested] = Signal(self.ports[requested]["width"], name=requested)
        return self._used_ports[requested]


class PortNotFoundException(Exception):
    pass
