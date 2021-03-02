from nmigen import *
from nmigen.hdl.ast import UserValue
from naps.util import yosys


def InstanceHelper(source_files, instance_name):
    return type(instance_name, (HelperedInstance,), {"instance_name": instance_name, "source_files": source_files})


class HelperedInstance(Elaboratable):
    def __init__(self, **kwargs):
        self.parameters = kwargs
        self.ports = yosys.get_verilog_module_ports(self.source_files, self.instance_name)
        self.signal_proxy = SignalProxy(self.ports)

    def __call__(self, *args, **kwargs):
        assert len(args) == 0
        self.parameters.update(**kwargs)
        return self

    def __getitem__(self, item):
        return self.signal_proxy.__getitem__(item)

    def __getattr__(self, item):
        return self.signal_proxy.__getattr__(item)

    def elaborate(self, platform):
        m = Module()

        named_ports = {
            "{}_{}".format(self.ports[name]["direction"], name): signal
            for name, signal in self.signal_proxy.used_ports.items()
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
        m.submodules.instance = Instance(self.instance_name, **named_ports, **parameters)

        return m


class SignalProxy(UserValue):
    def __init__(self, ports, path=""):
        super().__init__()

        self.ports = ports
        self.path = path

        self._used_ports = {}
        self.children = {}

    def lower(self):
        if self.path in self.ports:
            if self.path not in self._used_ports:
                self._used_ports[self.path] = Signal(self.ports[self.path]["width"], name=self.path)
            return self._used_ports[self.path]
        else:
            raise PortNotFoundException()

    @property
    def used_ports(self):
        child_ports = {}
        for c in self.children.values():
            child_ports = {**child_ports, **c.used_ports}
        return {**self._used_ports, **child_ports}

    def __getitem__(self, item):
        try:
            return self.lower()[item]
        except PortNotFoundException:
            return self.__getattr__(str(item))

    def __getattr__(self, item):
        if item.startswith("__"):
            return

        if item == "in_":
            item = "in"

        item = item.upper()

        if item not in self.children:
            self.children[item] = SignalProxy(self.ports, path=(self.path + item))
        return self.children[item]


class PortNotFoundException(Exception):
    pass
