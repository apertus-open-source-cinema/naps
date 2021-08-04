from pathlib import Path
from nmigen import Fragment, Module, ClockSignal, DomainRenamer
from nmigen.build.run import BuildProducts

from ... import *

__all__ = ["ZynqSocPlatform"]

from ...fatbitstream import File


class ZynqSocPlatform(SocPlatform):
    base_address = Address(0x4000_0000, 0, (0x7FFF_FFFF - 0x4000_0000) * 8)
    csr_domain = "axi_lite"

    def __init__(self, platform, use_axi_interconnect=False):
        from naps.vendor.xilinx_s7 import PS7

        super().__init__(platform)
        self.ps7 = PS7(here_is_the_only_place_that_instanciates_ps7=True)
        self.final_to_inject_subfragments.append((self.ps7, "ps7"))

        def peripherals_connect_hook(platform, top_fragment: Fragment, sames):
            from naps.cores.axi import AxiEndpoint, AxiLitePeripheralConnector, AxiFullToLiteBridge, AxiInterconnect

            if platform.peripherals:
                m = Module()
                platform.ps7.fck_domain(domain_name="axi_lite", requested_frequency=10e6)
                if not hasattr(platform, "is_sim"):  # we are not in a simulation platform
                    axi_full_port: AxiEndpoint = platform.ps7.get_axi_gp_master(ClockSignal(self.csr_domain))
                    axi_lite_bridge = m.submodules.axi_lite_bridge = DomainRenamer(self.csr_domain)(
                        AxiFullToLiteBridge(axi_full_port)
                    )
                    axi_lite_master = axi_lite_bridge.lite_master
                else:  # we are in a simulation platform
                    axi_lite_master = AxiEndpoint(addr_bits=32, data_bits=32, lite=True)
                    self.axi_lite_master = axi_lite_master

                if use_axi_interconnect:
                    interconnect = m.submodules.interconnect = DomainRenamer(self.csr_domain)(
                        AxiInterconnect(axi_lite_master)
                    )
                    for peripheral in platform.peripherals:
                        connector = DomainRenamer(self.csr_domain)(AxiLitePeripheralConnector(peripheral))
                        m.d.comb += interconnect.get_port().connect_downstream(connector.axi)
                        m.submodules += connector
                else:
                    aggregator = PeripheralsAggregator()
                    for peripheral in platform.peripherals:
                        aggregator.add_peripheral(peripheral)
                    connector = DomainRenamer(self.csr_domain)(AxiLitePeripheralConnector(aggregator))
                    m.d.comb += axi_lite_master.connect_downstream(connector.axi)
                    m.submodules.connector = connector
                platform.to_inject_subfragments.append((m, self.csr_domain))
        self.prepare_hooks.append(peripherals_connect_hook)

    def pack_bitstream_fatbitstream(self, name: str, build_products: BuildProducts):
        from .to_raw_bitstream import bit2bin
        bitstream = bit2bin(build_products.get(f"{name}.bit"))
        yield File("bitstream.bin", bitstream)
        yield f"cp bitstream.bin /usr/lib/firmware/{name}.bin"
        yield f"echo {name}.bin > /sys/class/fpga_manager/fpga0/firmware"

    def program_fatbitstream(self, name, **kwargs):
        program_fatbitstream_ssh(name, **kwargs)

    def pydriver_memory_accessor(self, memorymap):
        contents = (Path(__file__).parent / "memory_accessor_devmem.py").read_text()
        return contents + f"\nMemoryAccessor = lambda: DevMemAccessor(bytes={memorymap.byte_len})\n"
