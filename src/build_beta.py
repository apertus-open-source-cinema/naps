from nmigen import *

from devices.beta.beta_platform import BetaPlatform
from modules.xilinx.blocks import Ps7
from modules.hdmi import Hdmi
from modules.clocking import clock_manager as cm


class Top(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, plat):
        m = Module()

        m.domains += ClockDomain("sync")
        ps7 = m.submodules.ps7_wrapper = Ps7()
        m.d.comb += ClockSignal().eq(ps7.fclk.clk[0])
        m.d.comb += ResetSignal().eq(0)

        hdmi_plugin = plat.request("hdmi")
        m.submodules.hdmi = Hdmi(640, 480, 30, hdmi_plugin)

        return m


if __name__ == "__main__":
    p = BetaPlatform()


    from sys import argv
    do_build = "check" not in argv

    p.build(Top(), do_build=do_build)
