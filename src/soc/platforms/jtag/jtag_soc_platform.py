from nmigen import Fragment

from cores.jtag.jtag_peripheral_connector import JTAGPeripheralConnector
from soc.peripherals_aggregator import PeripheralsAggregator
from soc.memorymap import Address
from soc.soc_platform import SocPlatform


class JTAGSocPlatform(SocPlatform):
    base_address = Address(address=0x0000_0000, bit_offset=0, bit_len=0xFFFF_FFFF * 8)

    def __init__(self, platform):
        super().__init__(platform)
        self.init_script = ""

        def peripherals_connect_hook(platform, top_fragment: Fragment, sames):
            if platform.peripherals:
                aggregator = PeripheralsAggregator()
                for peripheral in platform.peripherals:
                    aggregator.add_peripheral(peripheral)

                jtag_controller = JTAGPeripheralConnector(aggregator)
                platform.to_inject_subfragments.append((jtag_controller, "jtag_controller"))
        self.prepare_hooks.append(peripherals_connect_hook)
