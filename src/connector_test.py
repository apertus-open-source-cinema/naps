from functools import lru_cache

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
                     Subsignal("tx", DiffPairs("7", "1", dir='o', conn=("pmod", "north")), Attrs(IOSTANDARD="LVDS_25")),
                     Subsignal("rx", DiffPairs("8", "2", dir='i', conn=("pmod", "north")), Attrs(IOSTANDARD="LVDS_25")),
                     )
        ])

    memory_map = {}
    next_addr = 0x4000_0000

    @lru_cache(maxsize=1024)  # for always emitting the same signal for the same name
    def axi_reg(self, name, width=8, writable=True):
        reg = axi_slave_on_master(self.m, self.axi_port, AxiLiteReg(width=width, base_address=self.next_addr, writable=writable, name=name))
        self.memory_map[name] = self.next_addr
        self.next_addr += 4
        return reg.reg

    def elaborate(self, plat: MicroR2Platform):
        m = self.m = Module()

        m.domains += ClockDomain("sync")
        ps7 = m.submodules.ps7_wrapper = Ps7()

        # clock_setup: the serdes clockdomain has double the frequency of fclk1
        m.d.comb += ClockSignal().eq(ps7.fclk.clk[0])
        pll = m.submodules.pll = RawPll(startup_wait=False, ref_jitter1=0.01, clkin1_period=8.0, clkfbout_mult=8,
                                        divclk_divide=1,
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
        axi_port = self.axi_port = ps7.maxigp[0]
        m.d.comb += axi_port.aclk.eq(ClockSignal())
        m.d.comb += ResetSignal().eq(~axi_port.aresetn)
        downgrade_axi_to_axi_lite(m, axi_port)

        self.connect_loopback_ressource(plat)
        self.axi_reg("test")
        m.d.comb += self.axi_reg("test_sink", writable=False).eq(0x42)

        # make the design resettable via a axi register
        reset = self.axi_reg("reset", width=1)
        for domain in ["sync", "serdes", "serdes_4x"]:
            m.d.comb += ResetSignal(domain).eq(reset)

        # loopback
        loopback = plat.request("loopback")

        ## sender side
        to_oserdes = Signal(8)

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
        m.d.comb += Cat(oserdes.d[i] for i in range(1, 9)).eq(to_oserdes)
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
        m.d.comb += idelay.ld.eq(self.axi_reg("idelay_ld"))
        m.d.comb += idelay.ldpipeen.eq(0)
        m.d.comb += idelay.ce.eq(0)
        m.d.comb += idelay.inc.eq(0)
        m.d.comb += idelay.cntvalue.in_.eq(self.axi_reg("idelay_cntvaluein"))
        m.d.comb += self.axi_reg("idelay_cntvalueout", writable=False).eq(idelay.cntvalue.out)
        m.d.comb += idelay.idatain.eq(loopback.rx)
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
        from_iserdes = Signal(8)
        m.d.comb += from_iserdes.eq(Cat(iserdes.q[i] for i in range(1, 9)))

        ## check logic
        last_received = self.axi_reg("last_received", writable=False)

        current_state = self.axi_reg("current_state", writable=False)
        training_cycles = self.axi_reg("trainig_cycles", writable=False)
        sliped_bits = self.axi_reg("sliped_bits", writable=False)
        error_cnt = self.axi_reg("error_cnt", 32, writable=False)
        success_cnt = self.axi_reg("error_cnt", 32, writable=False)

        with m.FSM(domain="serdes"):
            with m.State("TRAINING"):
                m.d.comb += current_state.eq(0)
                # start the link with correcting for the bitslip
                m.d.serdes += to_oserdes.eq(0b00001111)
                since_bitslip = Signal(2)
                m.d.serdes += training_cycles.eq(training_cycles+1)
                with m.If(iserdes.bitslip == 1):
                    m.d.serdes += iserdes.bitslip.eq(0)
                    m.d.serdes += since_bitslip.eq(0)
                with m.Elif(since_bitslip < 3):
                    m.d.serdes += since_bitslip.eq(since_bitslip + 1)
                with m.Elif(from_iserdes != 0b00001111):
                    m.d.serdes += iserdes.bitslip.eq(1)
                    m.d.serdes += sliped_bits.eq(sliped_bits+1)
                with m.Else():
                    m.d.serdes += to_oserdes.eq(0x00)
                    m.next = "RUNNING"
            with m.State("RUNNING"):
                m.d.comb += current_state.eq(1)

                m.d.serdes += to_oserdes.eq(to_oserdes+1)
                m.d.serdes += last_received.eq(from_iserdes)
                with m.If(from_iserdes == (last_received+1)[0:8]):
                    m.d.serdes += success_cnt.eq(success_cnt+1)
                with m.Else():
                    m.d.serdes += error_cnt.eq(error_cnt+1)

        # write the memory map
        with open("build/memorymap.csv", "w") as f:
            f.write("\n".join("{},\t0x{:06x}".format(k, v) for k, v in self.memory_map.items()))

        return m


if __name__ == "__main__":
    p = MicroR2Platform()
    p.build(
        Top(),
        name="connector_test",
        do_build=True,
        do_program=False,
        program_opts={"host": "10.42.0.1"},
    )
