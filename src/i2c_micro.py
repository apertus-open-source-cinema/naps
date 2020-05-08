from nmigen import *

from modules.axi.axi import AxiInterface
from modules.axi.axil_csr import AxilCsrBank
from modules.axi.axil_i2c_versatile_bitbang import AxilI2cVersatileBitbang
from modules.axi.full_to_lite import AxiFullToLiteBridge
from devices.micro.micro_r2_platform import MicroR2Platform
from modules.axi.interconnect import AxiInterconnect


class Top(Elaboratable):
    def elaborate(self, plat: MicroR2Platform):
        m = self.m = Module()

        ps7 = plat.get_ps7()
        ps7.fck_domain(requested_frequency=100e6)

        # axi setup
        m.domains += ClockDomain("axi_csr")
        m.d.comb += ClockSignal("axi_csr").eq(ClockSignal())
        axi_full_port: AxiInterface = ps7.get_axi_gp_master(0, ClockSignal("axi_csr"))
        axi_lite_bridge = m.submodules.axi_lite_bridge = DomainRenamer("axi_csr")(AxiFullToLiteBridge(axi_full_port))
        interconnect = m.submodules.interconnect = AxiInterconnect(axi_lite_bridge.lite_master)
        csr : AxilCsrBank
        csr = m.submodules.csr = DomainRenamer("axi_csr")(AxilCsrBank(interconnect.get_port()))

        # make the design resettable via a axi register
        reset = csr.reg("reset", width=1)
        m.d.comb += ResetSignal().eq(reset)

        # i2c
        i2c_pads = plat.request("i2c")
        i2c = m.submodules.i2c = AxilI2cVersatileBitbang(interconnect.get_port(), 0x4100_0000, i2c_pads)

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