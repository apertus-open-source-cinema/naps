from nmigen import *
import re

from util import yosys


class XilinxBlackbox(Elaboratable):
    """Wraps the a Xilinx ip as a convenient blackbox.
    """

    def __init__(self, **kwargs):
        self.module = self.module or self.__class__.__name__
        self.parameters = kwargs
        self.ports = yosys.get_module_ports(("+/xilinx/cells_xtra.v", "+/xilinx/cells_sim.v"), self.module)
        self.hierarchy = self._find_hierarchy(list(self.ports.keys()))
        # print(self.hierarchy)
        self.signal_proxy = SignalProxy(self.hierarchy, self.ports, path=self.module)

        assert type(self) != "XilinxBlackbox", "Do not instantiate `XilinxBlackbox` directly. Use its subclasses!"

    def elaborate(self, platform):
        m = Module()

        named_ports = {
            "{}_{}".format(self.ports[name]["direction"], name): signal
            for name, signal in self.signal_proxy.used_ports().items()
        }

        def legalize_parameter(parameter):
            if isinstance(parameter, bool):
                return "{}".format(parameter).upper()
            elif isinstance(parameter, str):
                return parameter.upper()
            else:
                return parameter

        legalized_parameters = {k: legalize_parameter(v) for k, v in self.parameters.items()}
        parameters = {"p_{}".format(k.upper()): v for k, v in legalized_parameters.items()}
        m.submodules.instance = Instance(self.module, **named_ports, **parameters)

        # print(named_ports)
        # print(parameters)

        return m

    def __getitem__(self, item):
        return self.signal_proxy.__getitem__(item)

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

                prefix = None
                if match := re.match("\\d", common_start):
                    prefix = match[0]
                elif match := re.match("[A-Z]*", common_start):
                    if len(match[0]) >= 3:
                        prefix = match[0]
                    else:
                        children = self.potential_children(match[0], h_name, hierarchy, n, signal_name)
                        if match[0].isalpha() and all(c.isdigit() or c == 'SELF' for c in children.keys()):
                            prefix = match[0]

                if prefix:
                    children = self.potential_children(prefix, h_name, hierarchy, n, signal_name)
                    if "" in children.keys():
                        continue

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
    def potential_children(common_start, h_name, hierarchy, n, signal_name):
        strip = lambda s: s.replace(common_start, "")
        children = None
        if isinstance(hierarchy[h_name], str):
            children = {strip(n): signal_name, strip(h_name): hierarchy[h_name]}
        else:
            children = {strip(n): signal_name, **{strip(k): v for k, v in hierarchy[h_name].items()}}
        if common_start == h_name:
            children = {**children, 'SELF': h_name}
        return children

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

    def __getitem__(self, item):
        if isinstance(item, int):
            item = str(item)

        item = item.upper()
        if item not in self.ports:
            return getattr(self, item)
            # raise KeyError("{} not found in {}".format(item, self.path))

        # do the real signal finding
        if item not in self._used_ports:
            self._used_ports[item] = Signal(self.ports[item]["width"], name=item)
        return self._used_ports[item]

    def __getattr__(self, item):
        if item.startswith("__"):
            return

        if item == "in_":
            item = "in"

        item = item.upper()

        if item not in self.hierarchy:
            raise KeyError("{} not found in {}".format(item, self.path))
        requested = self.hierarchy[item]
        if isinstance(requested, dict):
            if item not in self.children:
                self.children[item] = SignalProxy(requested, self.ports, path="{}.{}".format(self.path, item))
            return self.children[item]

        # do the real signal finding
        if requested not in self._used_ports:
            self._used_ports[requested] = Signal(self.ports[requested]["width"], name=requested)
        return self._used_ports[requested]


class PortNotFoundException(Exception):
    pass
