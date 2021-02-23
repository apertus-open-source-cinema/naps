# An experiment that outputs raw data from dram with a mipi dsi phy.
from nmigen import *
from nmigen.build import Subsignal, Attrs, Resource, DiffPairs
from nap import *
from nap.vendor.xilinx_s7 import Pll


class Top(Elaboratable):
    def __init__(self):
        self.buffer_len = ControlSignal(32, reset=0x1000)
        self.buffer_base = ControlSignal(32, reset=0x0f80_0000)
        self.buffers_written = StatusSignal(32)

    def elaborate(self, platform):
        m = Module()

        platform.ps7.fck_domain(100e6, "sync")

        platform.ps7.fck_domain(20e6, "pxclk")
        pll = m.submodules.pll = Pll(20e6, 60, 1, input_domain="pxclk")
        pll.output_domain("ddr_pxclk", 30)

        m.submodules.clocking = ClockingDebug("sync", "pxclk", "ddr_pxclk")

        # this experiment requires bodging the MicroR2 in a way that connects the southern plugin module
        # to a mipi DSI screen. Power and backlight have to be handled separated.
        platform.add_resources([
            Resource("mipi_dsi", 0,
                     Subsignal("clk", DiffPairs("25", "26", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS25")),
                     Subsignal("lane0", DiffPairs("27", "28", dir='o', conn=("expansion", 0)), Attrs(IOSTANDARD="LVCMOS25")),
            ),
        ])
        panel = platform.request("mipi_dsi")

        is_initialized = Signal()
        address_stream = BasicStream(32)
        buffer_counter = Signal(32)

        m.d.comb += address_stream.valid.eq(is_initialized)
        with m.If(~is_initialized):
            m.d.sync += address_stream.payload.eq(self.buffer_base)
            m.d.sync += is_initialized.eq(1)
        with m.Elif(address_stream.ready):
            with m.If(buffer_counter < self.buffer_len):
                m.d.sync += address_stream.payload.eq(address_stream.payload + 8)
                m.d.sync += buffer_counter.eq(buffer_counter + 1)
            with m.Else():
                m.d.sync += address_stream.payload.eq(self.buffer_base)
                m.d.sync += buffer_counter.eq(0)
                m.d.sync += self.buffers_written.eq(self.buffers_written + 1)

        p = Pipeline(m)
        p += StreamBuffer(address_stream)
        p += AxiReader(p.output)
        p += StreamGearbox(p.output, target_width=8)
        p += BufferedAsyncStreamFIFO(p.output, depth=2048, o_domain="pxclk")
        p += MipiMultiLaneTxPhy(p.output, panel.clk, [panel.lane0], ddr_domain="ddr_pxclk")

        return m


if __name__ == "__main__":
    cli(Top, runs_on=(MicroR2Platform,), possible_socs=(ZynqSocPlatform,))
