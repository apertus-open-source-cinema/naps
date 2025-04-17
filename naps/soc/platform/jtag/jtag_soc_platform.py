from pathlib import Path
from amaranth import Fragment, Signal, Module, ClockSignal
from amaranth.build.run import BuildProducts
from amaranth.vendor import LatticeMachXO2Platform

from ... import SocPlatform, Address, PeripheralsAggregator, PERIPHERAL_DOMAIN

__all__ = ["JTAGSocPlatform"]

from ...fatbitstream import File


class JTAGSocPlatform(SocPlatform):
    base_address = Address(address=0x0000_0000, bit_offset=0, bit_len=0xFFFF_FFFF * 8)

    def __init__(self, platform):
        super().__init__(platform)

        self.jtag_active = Signal()
        self.jtag_debug_signals = Signal(32)

        def peripherals_connect_hook(platform, top_fragment: Fragment, sames):
            from naps import JTAGPeripheralConnector
            if platform.peripherals:
                aggregator = PeripheralsAggregator()
                for peripheral in platform.peripherals:
                    aggregator.add_peripheral(peripheral)

                m = Module()
                m.submodules.jtag_controller = JTAGPeripheralConnector(aggregator, jtag_domain="jtag")

                m.d.comb += ClockSignal(PERIPHERAL_DOMAIN).eq(ClockSignal("jtag"))

                platform.to_inject_subfragments.append((m, "jtag"))

        self.prepare_hooks.append(peripherals_connect_hook)

    def pack_bitstream_fatbitstream(self, name: str, build_products: BuildProducts):
        if isinstance(self, LatticeMachXO2Platform):
            yield File("bitstream_jtag.svf", build_products.get(f"{name}_sram.svf"))
        else:
            yield File("bitstream_jtag.svf", build_products.get(f"{name}.svf"))
        yield from self._wrapped_platform.generate_openocd_conf()
        yield "openocd -f openocd.cfg -c 'svf -tap dut.tap -quiet -progress bitstream_jtag.svf; shutdown'"

    def pydriver_memory_accessor(self, _memorymap):
        return (Path(__file__).parent / "memory_accessor_openocd.py").read_text()
