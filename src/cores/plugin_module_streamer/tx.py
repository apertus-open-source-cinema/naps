# The PluginModuleStreamer{Sink,Source} tuple allows us to stream data from the main camera FPGA (Zynq) to some
# plugin module FPGA (i.e. the usb3 plugin module machxo2)

from nmigen import *

from cores.csr_bank import ControlSignal
from cores.primitives.xilinx_s7.clocking import Pll
from cores.primitives.xilinx_s7.io import DDRSerializer
from util.stream import StreamEndpoint


class PluginModuleStreamerTx(Elaboratable):
    def __init__(self, plugin_resource, input: StreamEndpoint, bitclk_domain, training_pattern=0b00000110):
        self.bitclk_domain = bitclk_domain
        self.plugin_lvds = plugin_resource
        self.input = input

        self.training_pattern = ControlSignal(reset=training_pattern)
        self.do_training = ControlSignal()

    def elaborate(self, platform):
        m = Module()

        sink = StreamEndpoint.like(self.input, is_sink=True)
        m.d.comb += sink.connect(self.input)
        
        m.d.comb += self.plugin_lvds.valid.eq(sink.valid & ~self.do_training)
        m.d.comb += sink.ready.eq(1)
        
        m.d.comb += self.plugin_lvds.clk_word.eq(ClockSignal())

        for i in range(4):
            value = Signal()
            m.submodules["lane{}".format(i)] = DDRSerializer(self.plugin_lvds["lvds{}".format(i)], value, ddr_clockdomain=self.bitclk_domain)
            with m.If(self.plugin_lvds.valid):
                m.d.comb += value.eq(sink.payload[0+(i*8):8+(i*8)])
            with m.Else():
                m.d.comb += value.eq(self.training_pattern)


        return m

