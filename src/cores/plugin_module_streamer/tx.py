# The PluginModuleStreamer{Sink,Source} tuple allows us to stream data from the main camera FPGA (Zynq) to some
# plugin module FPGA (i.e. the usb3 plugin module machxo2)

from nmigen import *

from cores.primitives.xilinx_s7.clocking import Pll
from cores.primitives.xilinx_s7.io import DDRSerializer
from util.stream import StreamEndpoint


class PluginModuleStreamerTx(Elaboratable):
    def __init__(self, input: StreamEndpoint, plugin_resource, training_pattern=0b00000110):
        self.training_pattern = training_pattern
        self.plugin_resource = plugin_resource
        self.input = input

    def elaborate(self, platform):
        m = Module()

        sink = StreamEndpoint.like(self.input, is_sink=True)
        m.d.comb += sink.connect(self.input)
        
        m.d.comb += self.plugin_resource.valid.eq(self.plugin_resource.ready & sink.valid)
        m.d.comb += sink.ready.eq(self.plugin_resource.ready)

        pll = m.submodules.pll = Pll(12.5e6, 80, 1)
        pll.output_domain("bitclk", 80 / 4)

        for i in range(4):
            value = Signal()
            m.submodules["lane{}".format(i)] = DDRSerializer(self.plugin_resource["lvds{}".format(i)], value, "bitclk")
            with m.If(self.plugin_resource.valid):
                m.d.comb += value.eq(sink.payload[0+(i*8):8+(i*8)])
            with m.Else():
                m.d.comb += value.eq(self.training_pattern)


        return m

