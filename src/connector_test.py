from nmigen import *
from nmigen.build import Resource, Subsignal, DiffPairs, Attrs

from modules.axi.axi import AxiInterface
from modules.axi.axil_csr import AxilCsrBank
from modules.axi.full_to_lite import AxiFullToLiteBridge
from modules.xilinx.Ps7 import Ps7
from modules.xilinx.blocks import Oserdes, RawPll, Bufg, Idelay, IdelayCtl, Iserdes
from devices.micro.micro_r2_platform import MicroR2Platform


class Top(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, plat: MicroR2Platform):
        m = self.module = Module()

        m.domains += ClockDomain("sync")
        ps7 = m.submodules.ps7_wrapper = Ps7()

        # clock_setup: the serdes clockdomain has double the frequency of fclk1
        m.d.comb += ClockSignal().eq(ps7.fclk.clk[0])
        pll = m.submodules.pll = RawPll(startup_wait=False, ref_jitter1=0.01, clkin1_period=8.0,
                                        clkfbout_mult=8, divclk_divide=1,
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
        m.domains += ClockDomain("axi")
        m.d.comb += ClockSignal("axi").eq(ClockSignal())
        axi_full_port: AxiInterface = ps7.get_axi_gp_master(0, ClockSignal("axi"))

        axi_lite_bridge = m.submodules.axi_lite_bridge = AxiFullToLiteBridge(axi_full_port)
        csr = m.submodules.csr = AxilCsrBank(axi_lite_bridge.lite_master)

        csr.reg("rw_test")
        test_counter_reg = csr.reg("test_counter", writable=False)
        m.d.sync += test_counter_reg.eq(test_counter_reg + 1)

        # make the design resettable via a axi register
        reset = csr.reg("reset_serdes", width=1)
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
        m.d.comb += Cat(oserdes.d[i] for i in reversed(range(1, 9))).eq(to_oserdes)  # reversed is needed!!1
        m.d.comb += loopback.tx.eq(oserdes.oq)

        ## reciver side
        bufg_idelay_refclk = m.submodules.bufg_idelay_refclk = Bufg()
        m.d.comb += bufg_idelay_refclk.i.eq(pll.clk.out[2])
        m.domains += ClockDomain("idelay_refclk")
        m.d.comb += ClockSignal("idelay_refclk").eq(bufg_idelay_refclk.o)
        idelay_ctl = m.submodules.idelay_ctl = IdelayCtl()
        m.d.comb += csr.reg("idelay_crl_rdy", writable=False, width=1).eq(idelay_ctl.rdy)
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
        m.d.comb += idelay.c.eq(ClockSignal())  # this is really the clock to which the control inputs are syncronous!
        m.d.comb += idelay.ld.eq(csr.reg("idelay_ld", width=1))
        m.d.comb += idelay.ldpipeen.eq(0)
        m.d.comb += idelay.ce.eq(0)
        m.d.comb += idelay.inc.eq(0)
        m.d.comb += idelay.cntvalue.in_.eq(csr.reg("idelay_cntvaluein", width=5))
        m.d.comb += csr.reg("idelay_cntvalueout", width=5, writable=False).eq(idelay.cntvalue.out)
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
        last_received = csr.reg("last_received", width=8, writable=False)

        current_state = csr.reg("current_state", writable=False)
        training_cycles = csr.reg("training_cycles", writable=False)
        slipped_bits = csr.reg("slipped_bits", writable=False)
        error_cnt = csr.reg("error_cnt", writable=False)
        success_cnt = csr.reg("success_cnt", writable=False)
        last_current_out = csr.reg("last_current_out", width=24, writable=False)
        test_pattern = csr.reg("test_patern", width=8, writable=True)

        with m.FSM(domain="serdes"):
            with m.State("TRAINING"):
                m.d.comb += current_state.eq(0)
                # start the link with correcting for the bitslip
                training_pattern = 0b00001111
                m.d.serdes += to_oserdes.eq(training_pattern)
                since_bitslip = Signal(2)
                m.d.serdes += training_cycles.eq(training_cycles + 1)
                with m.If(iserdes.bitslip == 1):
                    m.d.serdes += iserdes.bitslip.eq(0)
                    m.d.serdes += since_bitslip.eq(0)
                with m.Elif(since_bitslip < 3):
                    m.d.serdes += since_bitslip.eq(since_bitslip + 1)
                with m.Elif(from_iserdes != training_pattern):
                    m.d.serdes += iserdes.bitslip.eq(1)
                    m.d.serdes += slipped_bits.eq(slipped_bits + 1)
                with m.Else():
                    m.d.serdes += to_oserdes.eq(0x00)
                    m.next = "RUNNING"
            with m.State("RUNNING"):
                m.d.comb += current_state.eq(1)

                with m.If(test_pattern):
                    m.d.serdes += to_oserdes.eq(test_pattern)
                    with m.If(from_iserdes == test_pattern):
                        m.d.serdes += success_cnt.eq(success_cnt + 1)
                    with m.Else():
                        m.d.serdes += error_cnt.eq(error_cnt + 1)
                with m.Else():
                    m.d.serdes += to_oserdes.eq(to_oserdes + 1)
                    with m.If(from_iserdes == (last_received + 1)[0:8]):
                        m.d.serdes += success_cnt.eq(success_cnt + 1)
                    with m.Else():
                        m.d.serdes += error_cnt.eq(error_cnt + 1)

                m.d.serdes += last_received.eq(from_iserdes)
                m.d.comb += last_current_out.eq(Cat(last_received, from_iserdes, to_oserdes))

        return m


def connect_loopback_ressource(platform):
    platform.add_resources([
        Resource("loopback", 0,
                 # high speed serial lanes
                 Subsignal("tx", DiffPairs("1", "7", dir='o', conn=("pmod", "south")), Attrs(IOSTANDARD="LVDS_25")),
                 Subsignal("rx", DiffPairs("8", "2", dir='i', conn=("pmod", "south")), Attrs(IOSTANDARD="LVDS_25")),
                 )
    ])


if __name__ == "__main__":
    p = MicroR2Platform()
    connect_loopback_ressource(p)

    p.build(
        Top(),
        name=__file__.split(".")[0].split("/")[-1],
        do_build=True,
        do_program=True,
        program_opts={"host": "micro"}
    )
