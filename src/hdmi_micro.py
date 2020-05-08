from nmigen import *

from modules.axi.axi import AxiInterface
from modules.axi.axil_csr import AxilCsrBank
from modules.axi.full_to_lite import AxiFullToLiteBridge
from modules.hdmi.hdmi import Hdmi
from devices.micro.micro_r2_platform import MicroR2Platform


class Top(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, plat: MicroR2Platform):
        m = self.m = Module()

        ps7 = plat.get_ps7()
        ps7.fck_domain(requested_frequency=100e6)

        # axi setup
        m.domains += ClockDomain("axi_csr")
        m.d.comb += ClockSignal("axi_csr").eq(ClockSignal())
        axi_full_port: AxiInterface = ps7.get_axi_gp_master(0, ClockSignal("axi_csr"))
        axi_lite_bridge = m.submodules.axi_lite_bridge = DomainRenamer("axi_csr")(AxiFullToLiteBridge(axi_full_port))
        csr : AxilCsrBank
        csr = m.submodules.csr = DomainRenamer("axi_csr")(AxilCsrBank(axi_lite_bridge.lite_master))

        # make the design resettable via a axi register
        reset = csr.reg("reset", width=1)
        m.d.comb += ResetSignal().eq(reset)

        # hdmi
        hdmi_plugin = plat.request("hdmi")
        hdmi = m.submodules.hdmi = Hdmi(1920, 1080, 60, hdmi_plugin)

        csr.csr_for_module(hdmi.timing_generator, "hdmi_timing")
        csr.csr_for_module(hdmi.mmcm, "hdmi_mmcm")

        m.d.comb += hdmi_plugin.output_enable.eq(1)
        m.d.comb += hdmi_plugin.equalizer.eq(csr.reg("equalizer", width=2, reset=0b11))
        m.d.comb += hdmi_plugin.vcc_enable.eq(1)
        m.d.comb += hdmi_plugin.dcc_enable.eq(0)
        m.d.comb += hdmi_plugin.ddet.eq(0)

        return m


if __name__ == "__main__":
    p = MicroR2Platform()

    # connect the hdmi plugin module
    import devices.plugin_modules.hdmi as hdmi
    hdmi.hdmi_plugin_connect(p, "north", only_highspeed=False)

    p.build(
        Top(),
        name=__file__.split(".")[0].split("/")[-1],
        do_build=True,
        do_program=True,
        program_opts={"host": "micro"}
    )