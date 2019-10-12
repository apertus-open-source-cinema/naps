from nmigen import *
from nmigen.back import verilog

from modules.xilinx.blocks import Ps7
from devices.micro.micro_r2 import MicroR2Platform
from modules.hdmi import Hdmi


class Top(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, plat):
        m = Module()

        m.domains += ClockDomain("sync")
        ps7 = m.submodules.ps7_wrapper = Ps7()
        plat.add_clock_constraint(ps7.fclk.clk, 100e6)
        m.d.comb += ClockSignal().eq(ps7.fclk.clk[0])
        m.d.comb += ResetSignal().eq(0)


        hdmi_ressource = plat.request("hdmi")
        m.d.comb += hdmi_ressource.output_enable.eq(True)
        m.d.comb += hdmi_ressource.vcc_enable.eq(True)
        m.submodules += Hdmi(1920, 1080, 60, hdmi_ressource)

        return m


if __name__ == "__main__":
    p = MicroR2Platform()

    # connect the hdmi plugin module
    import devices.plugin_modules.hdmi as hdmi

    hdmi.connect(p, "plugin_n")

    from sys import argv

    if len(argv) > 1:
        assert argv[1] == "check"
        frag = Top().elaborate(p)
        verilog.convert(frag, name="top")
    else:
        p.build(Top())
