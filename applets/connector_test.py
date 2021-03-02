# an experiment to test highspeed connectors for data integrity
from nmigen import *
from nmigen.build import Resource, Subsignal, DiffPairs, Attrs
from naps import *
from naps.vendor.xilinx_s7.clocking import _Pll, BufG
from naps.vendor.xilinx_s7.io import _OSerdes, _IDelayCtrl, _IDelay, _ISerdes


class Top(Elaboratable):
    def elaborate(self, platform: ZynqSocPlatform):
        platform.add_resources([
            Resource("loopback", 0,
                     # high speed serial lanes
                     Subsignal("tx", DiffPairs("1", "7", dir='o', conn=("pmod", "south")), Attrs(IOSTANDARD="LVDS_25")),
                     Subsignal("rx", DiffPairs("8", "2", dir='i', conn=("pmod", "south")), Attrs(IOSTANDARD="LVDS_25")),
                     )
        ])

        m = Module()

        # clock_setup: the serdes clockdomain has double the frequency of fclk1
        platform.ps7.fck_domain()
        pll = m.submodules.pll = _Pll(startup_wait=False, ref_jitter1=0.01, clkin1_period=8.0,
                                      clkfbout_mult=8, divclk_divide=1,
                                      clkout0_divide=16, clkout0_phase=0.0,
                                      clkout1_divide=4, clkout1_phase=0.0)
        platform.ps7.fck_domain(requested_frequency=200e6, domain_name="pll_clk_in")
        m.d.comb += pll.clk.in_[1].eq(ClockSignal("pll_clk_in"))
        m.d.comb += pll.clk.fbin.eq(pll.clk.fbout)
        bufg_serdes = m.submodules.bufg_serdes = BufG(pll.clk.out[0])
        m.domains += ClockDomain("serdes")
        m.d.comb += ClockSignal("serdes").eq(bufg_serdes.o)
        bufg_serdes_4x = m.submodules.bufg_serdes_4x = BufG(pll.clk.out[1])
        m.domains += ClockDomain("serdes_4x")
        m.d.comb += ClockSignal("serdes_4x").eq(bufg_serdes_4x.o)


        # make the design resettable via a axi register
        reset_serdes = ControlSignal()
        for domain in ["sync", "serdes", "serdes_4x"]:
            m.d.comb += ResetSignal(domain).eq(reset_serdes)

        # loopback
        loopback = platform.request("loopback")

        ## sender side
        to_oserdes = Signal(8)

        oserdes = m.submodules.oserdes = _OSerdes(
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
        bufg_idelay_refclk = m.submodules.bufg_idelay_refclk = BufG(pll.clk.out[1])
        m.domains += ClockDomain("idelay_refclk")
        m.d.comb += ClockSignal("idelay_refclk").eq(bufg_idelay_refclk.o)
        idelay_ctl = m.submodules.idelay_ctl = _IDelayCtrl()
        m.d.comb += StatusSignal(name="idelay_crl_rdy").eq(idelay_ctl.rdy)
        m.d.comb += idelay_ctl.refclk.eq(ClockSignal("idelay_refclk"))
        m.d.comb += idelay_ctl.rst.eq(ResetSignal("idelay_refclk"))
        idelay = m.submodules.idelay = _IDelay(
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
        m.d.comb += idelay.ld.eq(ControlSignal(name="idelay_ld"))
        m.d.comb += idelay.ldpipeen.eq(0)
        m.d.comb += idelay.ce.eq(0)
        m.d.comb += idelay.inc.eq(0)
        m.d.comb += idelay.cntvalue.in_.eq(ControlSignal(5, name="idelay_cntvaluein"))
        m.d.comb += StatusSignal(5, name="idelay_cntvalueout").eq(idelay.cntvalue.out)
        m.d.comb += idelay.idatain.eq(loopback.rx)
        idelay_out = Signal()
        m.d.comb += idelay_out.eq(idelay.data.out)

        iserdes = m.submodules.iserdes = _ISerdes(
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
        last_received = StatusSignal(8, name="last_received")

        current_state = StatusSignal(32, name="current_state")
        training_cycles = StatusSignal(32, name="training_cycles")
        slipped_bits = StatusSignal(32, name="slipped_bits")
        error_cnt = StatusSignal(32, name="error_cnt")
        success_cnt = StatusSignal(32, name="success_cnt")
        last_current_out = StatusSignal(24, name="last_current_out")
        test_pattern = ControlSignal(8, name="test_patern")

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


if __name__ == "__main__":
    cli(Top, runs_on=(MicroR2Platform, ), possible_socs=(ZynqSocPlatform,))

