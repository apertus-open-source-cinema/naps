from nmigen import Fragment, Module

from cores.jtag.jtag_bus_slave import JTAGBusSlave
from soc.platforms.jtag.bus_slaves_aggregator import BusSlavesAggregator
from soc.memorymap import Address
from soc.soc_platform import SocPlatform


class JTAGSocPlatform(SocPlatform):
    base_address = Address(0x0000_0000, 0, 0xFFFF_FFFF * 8)

    def __init__(self, platform):
        super().__init__(platform)
        self.init_script = ""

        def bus_slaves_connect_hook(platform, top_fragment: Fragment, sames):
            bus_slaves = []

            def collect_bus_slaves(platform, fragment: Fragment, sames):
                module = sames.get_module(fragment)
                if module:
                    if hasattr(module, "bus_slave"):
                        bus_slaves.append(module.bus_slave)
                for (f, name) in fragment.subfragments:
                    collect_bus_slaves(platform, f, sames)

            collect_bus_slaves(platform, top_fragment, sames)

            if bus_slaves:
                ranges = [slave.memorymap.own_offset_normal_resources for slave in bus_slaves]
                for a in ranges:
                    for b in ranges:
                        if a is not b and a.collides(b):
                            raise AssertionError("{!r} overlaps with {!r}".format(a, b))

                aggregator = BusSlavesAggregator()
                for slave in bus_slaves:
                    aggregator.add_bus_slave(slave)

                jtag_bus_slave = JTAGBusSlave(aggregator.handle_read, aggregator.handle_write)
                platform.to_inject_subfragments.append((jtag_bus_slave, "jtag"))

        self.prepare_hooks.append(bus_slaves_connect_hook)

    def elaborateBusSlave(self, bus_slave):
        m = Module()
        m.bus_slave = bus_slave
        return m