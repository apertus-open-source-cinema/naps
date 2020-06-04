from nmigen import Fragment, Module, ClockSignal, DomainRenamer

from soc.axi import AxiInterface
from soc.axi.full_to_lite import AxiFullToLiteBridge
from soc.axi.interconnect import AxiInterconnect
from soc.axi.lite_slave import AxiLiteSlave
from soc.memorymap import Address
from soc.soc_platform import SocPlatform
from soc.tracing_elaborate import ElaboratableSames
from .program_bitstream_ssh import program_bitstream_ssh
from xilinx.ps7 import Ps7


class ZynqSocPlatform(SocPlatform):
    base_address = Address(0x4000_0000, 0, (0x7FFF_FFFF - 0x4000_0000) * 8)

    def __init__(self, platform):
        super().__init__(platform)
        self.ps7 = None
        self.init_script = ""
        platform.toolchain_program = lambda *args, **kwargs: program_bitstream_ssh(self, *args, **kwargs)

        def bus_slaves_connect_hook(platform, top_fragment: Fragment, sames: ElaboratableSames):
            bus_slaves = []

            def collect_bus_slaves(platform, fragment: Fragment, sames: ElaboratableSames):
                module = sames.get_module(fragment)
                if module:
                    if hasattr(module, "bus_slave"):
                        bus_slave, memorymap = module.bus_slave
                        bus_slaves.append((bus_slave, memorymap))
                for (f, name) in fragment.subfragments:
                    collect_bus_slaves(platform, f, sames)

            collect_bus_slaves(platform, top_fragment, sames)
            if bus_slaves:
                # generate all the connections
                m = Module()
                ps7 = self.get_ps7()
                ps7.fck_domain(domain_name="axi_csr", requested_frequency=100e6)
                if not hasattr(platform, "is_sim"):
                    axi_full_port: AxiInterface = ps7.get_axi_gp_master(0, ClockSignal("axi_csr"))
                    axi_lite_bridge = m.submodules.axi_lite_bridge = DomainRenamer("axi_csr")(
                        AxiFullToLiteBridge(axi_full_port)
                    )
                    axi_lite_master = axi_lite_bridge.lite_master
                else:  # we are in a simulation platform
                    axi_lite_master = AxiInterface(addr_bits=32, data_bits=32, master=True, lite=True)
                    self.axi_lite_master = axi_lite_master
                interconnect = m.submodules.interconnect = DomainRenamer("axi_csr")(
                    AxiInterconnect(axi_lite_master)
                )

                ranges = [memorymap.own_offset_normal_resources for slave, memorymap in bus_slaves]
                for a in ranges:
                    for b in ranges:
                        if a is not b and a.collides(b):
                            raise AssertionError("{!r} overlaps with {!r}".format(a, b))

                for slave, slave_memorymap in bus_slaves:
                    slave.address_range = slave_memorymap.own_offset_normal_resources.range()
                    slave = DomainRenamer("axi_csr")(slave)
                    m.d.comb += interconnect.get_port().connect_slave(slave.axi)
                    m.submodules += slave
                platform.to_inject_subfragments.append((m, "axi_lite"))
        self.prepare_hooks.append(bus_slaves_connect_hook)

    def BusSlave(self, handle_read, handle_write, *, memorymap):
        bus_slave = AxiLiteSlave(handle_read, handle_write)

        m = Module()  # we will pick this empty module, that is just a marker up later in the prepare step
        m.bus_slave = (bus_slave, memorymap)
        return m

    def get_ps7(self) -> Ps7:
        if self.ps7 is None:
            self.ps7 = Ps7(here_is_the_only_place_that_instanciates_ps7=True)
            self.final_to_inject_subfragments.append((self.ps7, "ps7"))
        return self.ps7