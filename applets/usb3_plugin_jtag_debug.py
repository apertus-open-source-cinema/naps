# An experiment for debugging the JTAG interface on the usb3 plugin module by using the USB3 output
# as a usb3 output.
from nmigen import *
from naps import *
from naps.vendor.lattice_machxo2 import Osc


class Top(Elaboratable):
    def __init__(self):
        self.counter = StatusSignal(32)
        self.test_reg32 = ControlSignal(32)

    def elaborate(self, platform):
        m = Module()
        m.submodules.osc = Osc(freq=53.2e6)
        m.d.sync += self.counter.eq(self.counter + 1)
        m.d.comb += platform.request("led", 0).eq(self.counter[24])

        debug_stream_source = BasicStream(32)
        m.d.comb += debug_stream_source.valid.eq(1)
        m.d.comb += debug_stream_source.payload.eq(platform.jtag_debug_signals)

        ft601 = platform.request("ft601")
        m.submodules.ft601 = FT601StreamSink(ft601, debug_stream_source, domain_name="ft601")

        return m


if __name__ == "__main__":
    cli(Top, runs_on=(Usb3PluginPlatform,), possible_socs=(JTAGSocPlatform,))
