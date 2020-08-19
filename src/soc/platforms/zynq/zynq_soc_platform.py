from nmigen import Fragment, Module, ClockSignal, DomainRenamer

from cores.axi import AxiEndpoint
from cores.axi.axi_lite_peripheral_connector import AxiLitePeripheralConnector
from cores.axi.full_to_lite import AxiFullToLiteBridge
from cores.axi.interconnect import AxiInterconnect
from soc.memorymap import Address
from soc.soc_platform import SocPlatform
from cores.primitives.xilinx_s7.ps7 import PS7
from .program_bitstream_ssh import program_bitstream_ssh


class ZynqSocPlatform(SocPlatform):
    base_address = Address(0x4000_0000, 0, (0x7FFF_FFFF - 0x4000_0000) * 8)

    def __init__(self, platform):
        super().__init__(platform)
        self.ps7 = PS7(here_is_the_only_place_that_instanciates_ps7=True)
        self.final_to_inject_subfragments.append((self.ps7, "ps7"))

        self.init_script = ""

        def peripherals_connect_hook(platform, top_fragment: Fragment, sames):
            if platform.peripherals:
                m = Module()
                platform.ps7.fck_domain(domain_name="axi_lite", requested_frequency=100e6)
                if not hasattr(platform, "is_sim"):  # we are not in a simulation platform
                    axi_full_port: AxiEndpoint = platform.ps7.get_axi_gp_master(ClockSignal("axi_lite"))
                    axi_lite_bridge = m.submodules.axi_lite_bridge = DomainRenamer("axi_lite")(
                        AxiFullToLiteBridge(axi_full_port)
                    )
                    axi_lite_master = axi_lite_bridge.lite_master
                else:  # we are in a simulation platform
                    axi_lite_master = AxiEndpoint(addr_bits=32, data_bits=32, master=True, lite=True)
                    self.axi_lite_master = axi_lite_master
                interconnect = m.submodules.interconnect = DomainRenamer("axi_lite")(
                    AxiInterconnect(axi_lite_master)
                )

                for peripheral in platform.peripherals:
                    controller = DomainRenamer("axi_lite")(AxiLitePeripheralConnector(peripheral))
                    m.d.comb += interconnect.get_port().connect_slave(controller.axi)
                    m.submodules += controller
                platform.to_inject_subfragments.append((m, "axi_lite"))
        self.prepare_hooks.append(peripherals_connect_hook)

    def toolchain_program(self, *args, **kwargs):
        program_bitstream_ssh(self, *args, **kwargs)