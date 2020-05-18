from datetime import datetime

from nmigen import *

from modules.hdmi.hdmi import Hdmi
from devices.micro.micro_r2_platform import MicroR2Platform
from soc.reg_types import ControlSignal
from soc.zynq.ZynqSocPlatform import ZynqSocPlatform
from util.cvt import generate_modeline


class Top(Elaboratable):
    def __init__(self):
        self.reset = ControlSignal()

    def elaborate(self, plat: ZynqSocPlatform):
        m = Module()

        ps7 = plat.get_ps7()
        ps7.fck_domain(requested_frequency=100e6)
        m.d.comb += ResetSignal().eq(self.reset)

        hdmi_plugin = plat.request("hdmi")
        m.submodules.hdmi = Hdmi(hdmi_plugin, modeline='Modeline "Mode 1" 148.500 1920 2008 2052 2200 1080 1084 1089 1125 +hsync +vsync')

        return m


if __name__ == "__main__":
    p = ZynqSocPlatform(MicroR2Platform())

    # connect the hdmi plugin module
    import devices.plugin_modules.hdmi as hdmi
    hdmi.hdmi_plugin_connect(p, "north", only_highspeed=False)

    p.build(
        Top(),
        name=__file__.split(".")[0].split("/")[-1] + datetime.now().strftime("-%d-%b-%Y--%H-%M-%S"),
        do_build=False,
        do_program=False,
        program_opts={"host": "micro"}
    )