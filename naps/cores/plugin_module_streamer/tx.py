# The PluginModuleStreamer{Sink,Source} tuple allows us to stream data from the main camera FPGA (Zynq) to some
# plugin module FPGA (i.e. the usb3 plugin module machxo2)

from nmigen import *
from naps import BasicStream, ControlSignal
from naps.cores import InflexibleSinkDebug
from naps.vendor.xilinx_s7 import DDRSerializer

__all__ = ["PluginModuleStreamerTx"]


class PluginModuleStreamerTx(Elaboratable):
    def __init__(self, plugin_resource, input: BasicStream, bitclk_domain, training_pattern=0b00010110):
        self.bitclk_domain = bitclk_domain
        self.plugin_resource = plugin_resource
        self.input = input

        self.training_pattern = ControlSignal(8, reset=training_pattern)
        self.do_training = ControlSignal(reset=1)

    def elaborate(self, platform):
        m = Module()
        
        m.d.comb += self.input.ready.eq(~self.do_training)
        m.submodules.inflexible_sink_debug = InflexibleSinkDebug(self.input)

        valid = Signal()
        m.d.comb += valid.eq(self.input.valid & ~self.do_training)
        m.submodules.lane_clock = DDRSerializer(0b00001111, self.plugin_resource.clk_word, ddr_domain=self.bitclk_domain, msb_first=True)
        m.submodules.lane_valid = DDRSerializer(Repl(valid, 8), self.plugin_resource.valid, ddr_domain=self.bitclk_domain, msb_first=True)
        for i in range(4):
            value = Signal(8)
            m.submodules["lane{}".format(i)] = DDRSerializer(value, self.plugin_resource["lane{}".format(i)], ddr_domain=self.bitclk_domain, msb_first=True)
            with m.If(valid):
                m.d.comb += value.eq(self.input.payload[0+(i*8):8+(i*8)])
            with m.Else():
                m.d.comb += value.eq(self.training_pattern)

        return m
