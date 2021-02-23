from nmigen import *
from nap import nAny
from ..generic.jtag import JTAG as GenericJTAG


class JTAG(GenericJTAG.implementation):
    # the lattice jtag primitive is rather wired and has a one cycle delay on tdi

    def elaborate(self, platform):
        m = Module()

        # our whole clocking setup introduces 1 cycle delay into our jtag chain. This is inavoidable for a robust jtag implementation with JTAGF
        cd_n = ClockDomain(self.jtag_domain, clk_edge="neg")  # we need to sample jtdi at the falling edge since it seems to have a ff on the rising edge
        m.domains += cd_n
        platform.add_clock_constraint(cd_n.clk, 1e6)

        cd_p = ClockDomain(self.jtag_domain + '_p', clk_edge="pos")
        m.domains += cd_p
        m.d.comb += cd_p.clk.eq(cd_n.clk)
        platform.add_clock_constraint(cd_p.clk, 1e6)

        # we need to set jtdo on the rising edge since it seems to have a ff on the falling edge
        jtdo = Signal()
        m.d[cd_p.name] += jtdo.eq(self.tdo)


        active_signals = [Signal() for _ in range(4)]
        if hasattr(platform, "jtag_active"):
            m.d.comb += platform.jtag_active.eq(nAny(active_signals))

            m.d.comb += platform.jtag_debug_signals[0].eq(cd_n.clk)
            m.d.comb += platform.jtag_debug_signals[1].eq(self.tdo)
            m.d.comb += platform.jtag_debug_signals[2].eq(self.tdi)
            m.d.comb += platform.jtag_debug_signals[3].eq(self.shift)
            m.d.comb += platform.jtag_debug_signals[5:6].eq(Cat(*active_signals))

        m.submodules.jtag_primitive = Instance(
            "JTAGF",
            i_JTDO1=jtdo,  # FF on negedge (sampled then); need to setup on posedge
            o_JTDI=self.tdi,  # FF on posedge; sample on negedge
            o_JTCK=cd_n.clk,
            o_JSHIFT=self.shift,  # no FF?

            o_JRTI1=active_signals[0],
            o_JRTI2=active_signals[1],
            o_JCE1=active_signals[2],
            o_JCE2=active_signals[3],
        )

        return m
