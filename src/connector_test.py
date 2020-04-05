from nmigen import *
from nmigen.build import Resource, Subsignal, DiffPairs, Attrs

from modules.axi.axil_reg import AxiLiteReg
from modules.axi.helper import downgrade_axi_to_axi_lite, axi_slave_on_master
from modules.xilinx.blocks import Ps7, Oserdes, RawPll, Bufg, Idelay, IdelayCtl, Iserdes
from devices.micro.micro_r2_platform import MicroR2Platform


class Top(Elaboratable):
    def __init__(self):
        pass

    def connect_loopback_ressource(self, platform):
        platform.add_resources([
            Resource("loopback", 0,
                     # high speed serial lanes
                     Subsignal("tx", DiffPairs("1", "7", dir='o', conn=("pmod", "north")), Attrs(IOSTANDARD="LVDS_25")),
                     Subsignal("rx", DiffPairs("2", "8", dir='i', conn=("pmod", "north")), Attrs(IOSTANDARD="LVDS_25")),
                     )
        ])

    def elaborate(self, plat: MicroR2Platform):
        m = Module()

        m.domains += ClockDomain("sync")
        ps7 = m.submodules.ps7_wrapper = Ps7()


        # clock_setup: the serdes clockdomain has double the frequency of fclk1
        m.d.comb += ClockSignal().eq(ps7.fclk.clk[0])
        pll = m.submodules.pll = RawPll(startup_wait=False, ref_jitter1=0.01, clkin1_period=8.0, clkfbout_mult=8, divclk_divide=1,
                                        clkout0_divide=16, clkout0_phase=0.0,
                                        clkout1_divide=4, clkout1_phase=0.0)
        m.d.comb += pll.clk.in1.eq(ps7.fclk.clk[1])
        m.d.comb += pll.clk.fbin.eq(pll.clk.fbout)
        bufg_serdes = m.submodules.bufg_serdes = Bufg()
        m.d.comb += bufg_serdes.i.eq(pll.clk.out[0])
        m.domains += ClockDomain("serdes")
        m.d.comb += ClockSignal("serdes").eq(bufg_serdes.o)
        bufg_serdes_4x = m.submodules.bufg_serdes_4x = Bufg()
        m.d.comb += bufg_serdes_4x.i.eq(pll.clk.out[1])
        m.domains += ClockDomain("serdes_4x")
        m.d.comb += ClockSignal("serdes_4x").eq(bufg_serdes_4x.o)



        # axi setup
        axi_port = ps7.maxigp[0]
        m.d.comb += axi_port.aclk.eq(ClockSignal())
        m.d.comb += ResetSignal().eq(~axi_port.aresetn)
        downgrade_axi_to_axi_lite(m, axi_port)

        test_reg1 = axi_slave_on_master(m, axi_port, AxiLiteReg(width=8, base_address=0x4000_0000))
        test_reg2 = axi_slave_on_master(m, axi_port, AxiLiteReg(width=8, base_address=0x4000_0001))
        m.d.comb += test_reg1.reg.eq(test_reg2.reg)


        # loopback
        self.connect_loopback_ressource(plat)
        loopback = plat.request("loopback")

        ## sender side
        counter = Signal(8)
        m.d.serdes += counter.eq(counter+1)

        oserdes = m.submodules.oserdes = Oserdes(
            data_width=8,
            tristate_width=1,
            data_rate_oq="ddr",
            serdes_mode="master",
            data_rate_tq="buf"
        )
        m.d.comb += oserdes.oce.eq(1)
        m.d.comb += oserdes.clk.eq(ClockSignal("serdes_4x"))
        m.d.comb += oserdes.clkdiv.eq(ClockSignal("serdes"))
        m.d.comb += oserdes.rst.eq(ResetSignal("serdes"))
        m.d.comb += Cat(oserdes.d[i] for i in range(1, 9)).eq(counter)
        m.d.comb += loopback.tx.eq(oserdes.oq)

        ## reciver side
        m.domains += ClockDomain("idelay_refclk")
        m.d.comb += ClockSignal("idelay_refclk").eq(ps7.fclk.clk[2])
        idelay_ctl = m.submodules.idelay_ctl = IdelayCtl()
        m.d.comb += idelay_ctl.refclk.eq(ClockSignal("idelay_refclk"))
        m.d.comb += idelay_ctl.rst.eq(ResetSignal("idelay_refclk"))
        idelay = m.submodules.idelay = Idelay(
            delay_src="iDataIn",
            signal_pattern="data",
            cinvctrl_sel=False,
            high_performance_mode=True,
            refclk_frequency=200.0,
            pipe_sel=False,
            idelay_type="var_load",
            idelay_value=0
        )
        m.d.comb += idelay.c.eq(ClockSignal())
        #m.d.comb += idelay.ld.eq() # TODO Axi reg
        m.d.comb += idelay.ldPipeEn.eq(0)
        m.d.comb += idelay.ce.eq(0)
        # m.d.comb += idelay.increment.eq(0) TODO: this port does not exist
        #m.d.comb += idelay.cntValueIn.eq() # TODO Axi reg
        #m.d.comb += lal.eq(idelay.cntValueOut) # TODO Axi reg
        m.d.comb += idelay.iDataIn.eq(loopback.rx)
        idelay_out = Signal()
        m.d.comb += idelay_out.eq(idelay.data.out)

        iserdes = m.submodules.iserdes = Iserdes(
            data_width=8,
            data_rate="ddr",
            serdes_mode="master",
            interface_type="networking",
            num_ce=1,
            iobDelay="ifd",
        )
        m.d.comb += iserdes.ddly.eq(idelay_out)
        m.d.comb += iserdes.ce[1].eq(1)
        m.d.comb += iserdes.clk.eq(ClockSignal("serdes_4x"))
        m.d.comb += iserdes.clkb.eq(~ClockSignal("serdes_4x"))
        m.d.comb += iserdes.rst.eq(ResetSignal("serdes"))
        m.d.comb += iserdes.clkdiv.eq(ClockSignal("serdes"))
        #m.d.comb += iserdes.bitslip.eq(0) # TODO: AXI
        iserdes_out = Signal(8)
        m.d.comb += iserdes_out.eq(Cat(iserdes.q[i] for i in range(1, 9)))


        ## check logic


        return m


if __name__ == "__main__":
    # dut = Top()
    # print(verilog.convert(dut))

    p = MicroR2Platform()
    p.build(Top(), do_build=False)
