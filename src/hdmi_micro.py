from nmigen import *
from nmigen.build import Resource, Subsignal, DiffPairs, Attrs

from modules.axi.axil_reg import AxiLiteReg
from modules.axi.helper import downgrade_axi_to_axi_lite, axi_slave_on_master
from modules.hdmi import Hdmi
from modules.xilinx.blocks import Ps7, Oserdes, RawPll, Bufg, Idelay, IdelayCtl, Iserdes
from devices.micro.micro_r2_platform import MicroR2Platform


class Top(Elaboratable):
    def __init__(self):
        pass

    memory_map = {}
    next_addr = 0x4000_0000

    def axi_reg(self, name, width=32, writable=True):
        reg = axi_slave_on_master(self.m, self.axi_port, DomainRenamer("axi")(AxiLiteReg(width=width, base_address=self.next_addr, writable=writable, name=name)))
        assert name not in self.memory_map
        self.memory_map[name] = self.next_addr
        self.next_addr += 4
        return reg.reg

    def elaborate(self, plat: MicroR2Platform):
        m = self.m = Module()

        m.domains += ClockDomain("sync")
        ps7 = m.submodules.ps7_wrapper = Ps7()

        # clock_setup
        m.d.comb += ClockSignal().eq(ps7.fclk.clk[0])

        # axi setup
        m.domains += ClockDomain("axi")
        m.d.comb += ClockSignal("axi").eq(ClockSignal())
        axi_port = self.axi_port = ps7.maxigp[0]
        m.d.comb += axi_port.aclk.eq(ClockSignal("axi"))
        m.d.comb += ResetSignal("axi").eq(~axi_port.aresetn)
        downgrade_axi_to_axi_lite(m, axi_port)

        self.axi_reg("rw_test")
        test_counter_reg = self.axi_reg("test_counter", writable=False)
        m.d.sync += test_counter_reg.eq(test_counter_reg + 1)

        # make the design resettable via a axi register
        reset = self.axi_reg("reset", width=1)
        for domain in ["sync"]:
            m.d.comb += ResetSignal(domain).eq(reset)

        # hdmi
        hdmi_plugin = plat.request("hdmi")
        m.submodules.hdmi = Hdmi(1920, 1080, 60, hdmi_plugin)
        m.d.comb += hdmi_plugin.output_enable.eq(1)
        m.d.comb += hdmi_plugin.equalizer.eq(0b11)
        m.d.comb += hdmi_plugin.vcc_enable.eq(1)
        m.d.comb += hdmi_plugin.dcc_enable.eq(0)
        m.d.comb += hdmi_plugin.ddet.eq(0)



        # write the memory map
        plat.add_file(
            "regs.csv",
            "\n".join("{},\t0x{:06x}".format(k, v) for k, v in self.memory_map.items())
        )
        plat.add_file(
            "regs.sh",
            "\n".join("export r_{}=0x{:06x}".format(k, v) for k, v in self.memory_map.items()) + "\n\n" +
            "\n".join("echo {}: $(devmem2 0x{:06x} | sed -r 's|.*: (.*)|\\1|' | tail -n1)".format(k, v) for k, v in
                        self.memory_map.items()) + "\n\n" +
            plat.extra_lines if hasattr(plat, "extra_lines") else ""
        )

        return m


if __name__ == "__main__":
    p = MicroR2Platform()

    # connect the hdmi plugin module
    import devices.plugin_modules.hdmi as hdmi
    hdmi.hdmi_plugin_connect(p, "north", only_highspeed=False)

    p.extra_lines = ""

    p.build(
        Top(),
        name="hdmi_micro",
        do_build=True,
        do_program=True,
    )
