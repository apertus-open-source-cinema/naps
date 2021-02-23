from os.path import join, dirname
from nmigen import Fragment, Signal
from ... import SocPlatform, Address, PeripheralsAggregator

__all__ = ["JTAGSocPlatform"]


class JTAGSocPlatform(SocPlatform):
    base_address = Address(address=0x0000_0000, bit_offset=0, bit_len=0xFFFF_FFFF * 8)
    pydriver_memory_accessor = open(join(dirname(__file__), "memory_accessor_openocd.py")).read()

    def __init__(self, platform):
        super().__init__(platform)

        self.jtag_active = Signal()
        self.jtag_debug_signals = Signal(32)

        def peripherals_connect_hook(platform, top_fragment: Fragment, sames):
            from nap import JTAGPeripheralConnector
            if platform.peripherals:
                aggregator = PeripheralsAggregator()
                for peripheral in platform.peripherals:
                    aggregator.add_peripheral(peripheral)

                jtag_controller = JTAGPeripheralConnector(aggregator)
                platform.to_inject_subfragments.append((jtag_controller, "jtag_controller"))

        self.prepare_hooks.append(peripherals_connect_hook)

    def pack_bitstream_fatbitstream(self, builder):
        builder.append_self_extracting_blob_from_file("{{name}}_sram.svf", "bitstream_jtag.svf")
        builder.append_command("openocd -f openocd.cfg -c 'svf -tap dut.tap -quiet -progress bitstream_jtag.svf; shutdown'\n")
