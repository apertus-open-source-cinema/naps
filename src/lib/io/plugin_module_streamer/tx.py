# The PluginModuleStreamer{Sink,Source} tuple allows us to stream data from the main camera FPGA (Zynq) to some
# plugin module FPGA (i.e. the usb3 plugin module machxo2)

from nmigen import *

from lib.bus.stream.stream import Stream
from lib.peripherals.csr_bank import ControlSignal
from lib.primitives.xilinx_s7.io import DDRSerializer


class PluginModuleStreamerTx(Elaboratable):
    def __init__(self, plugin_resource, input: Stream, bitclk_domain, training_pattern=0b00000110):
        self.bitclk_domain = bitclk_domain
        self.plugin_lvds = plugin_resource
        self.input = input

        self.training_pattern = ControlSignal(reset=training_pattern)
        self.do_training = ControlSignal()

    def elaborate(self, platform):
        m = Module()
        
        m.d.comb += self.plugin_lvds.valid.eq(self.input.valid & ~self.do_training)
        m.d.comb += self.input.ready.eq(1)
        
        m.d.comb += self.plugin_lvds.clk_word.eq(ClockSignal())

        for i in range(4):
            value = Signal()
            m.submodules["lane{}".format(i)] = DDRSerializer(self.plugin_lvds["lvds{}".format(i)], value, ddr_clockdomain=self.bitclk_domain)
            with m.If(self.plugin_lvds.valid):
                m.d.comb += value.eq(self.input.payload[0+(i*8):8+(i*8)])
            with m.Else():
                m.d.comb += value.eq(self.training_pattern)

        return m

