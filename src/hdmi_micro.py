from datetime import datetime

from nmigen import *

from modules.hdmi import Hdmi
from devices.micro.micro_r2_platform import MicroR2Platform
from soc.zynq.ZynqSocPlatform import ZynqSocPlatform
from util.cvt import generate_modeline


class Top(Elaboratable):
    def elaborate(self, plat: ZynqSocPlatform):
        m = Module()

        ps7 = plat.get_ps7()
        ps7.fck_domain(requested_frequency=100e6)

        # axi setup
        #csr: AutoCsrBank = DomainRenamer("axi_lite")(AutoCsrBank(ps7.get_axi_lite_port()))
        #m.submodules.csr = csr

        # make the design resettable via a axi register
        #reset = csr.reg("reset", width=1)
        #m.d.comb += ResetSignal().eq(reset)

        # hdmi
        hdmi_plugin = plat.request("hdmi")
        hdmi = m.submodules.hdmi = Hdmi(hdmi_plugin, modeline='Modeline "Mode 1" 148.500 1920 2008 2052 2200 1080 1084 1089 1125 +hsync +vsync')

        #csr.csr_for_module(hdmi.timing_generator, "hdmi_timing")

        m.d.comb += hdmi_plugin.output_enable.eq(1)
        #m.d.comb += hdmi_plugin.equalizer.eq(csr.reg("equalizer", width=2, reset=0b11))
        m.d.comb += hdmi_plugin.equalizer.eq(0b11)
        m.d.comb += hdmi_plugin.vcc_enable.eq(1)
        m.d.comb += hdmi_plugin.dcc_enable.eq(0)
        m.d.comb += hdmi_plugin.ddet.eq(0)

        return m


if __name__ == "__main__":
    p = ZynqSocPlatform(MicroR2Platform())

    # connect the hdmi plugin module
    import devices.plugin_modules.hdmi as hdmi
    hdmi.hdmi_plugin_connect(p, "north", only_highspeed=False)

    p.build(
        Top(),
        name=__file__.split(".")[0].split("/")[-1] + datetime.now().strftime("-%d-%b-%Y--%H-%M-%S"),
        do_build=True,
        do_program=True,
        program_opts={"host": "micro"}
    )