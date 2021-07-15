from nmigen import *
from .s7_phy import HostTrainer, Cmv12kPhy

__all__ = ["Cmv12kRx"]

class Cmv12kRx(Elaboratable):
    def __init__(self, sensor, num_lanes=32, bits=12, domain="cmv12k"):
        self.domain = domain
        self.lvds_outclk = sensor.lvds_outclk
        self.lanes = Cat(getattr(sensor, f"lvds_{l}") for l in range(num_lanes))
        self.lane_ctrl = sensor.lvds_ctrl
        self.bits = bits

        self.trainer = HostTrainer(num_lanes)
        self.phy = Cmv12kPhy(num_lanes=num_lanes, bits=self.bits, domain=domain)

    def elaborate(self, platform):
        m = Module()

        # temp clock setup
        platform.ps7.fck_domain(200e6, self.domain+"_delay_ref")
        m.domains += ClockDomain(self.domain+"_ctrl")
        m.d.comb += ClockSignal(self.domain+"_ctrl").eq(ClockSignal(platform.csr_domain))

        phy = m.submodules.phy = self.phy
        trainer = m.submodules.trainer = self.trainer

        m.d.comb += [
            phy.outclk.eq(self.lvds_outclk),
            phy.lanes.eq(Cat(self.lanes, self.lane_ctrl)),

            phy.lane_pattern.eq(self.trainer.lane_pattern),
            phy.lane_delay_reset.eq(self.trainer.lane_delay_reset),
            phy.lane_delay_inc.eq(self.trainer.lane_delay_inc),
            phy.lane_bitslip.eq(self.trainer.lane_bitslip),
            phy.outclk_delay_reset.eq(self.trainer.outclk_delay_reset),
            phy.outclk_delay_inc.eq(self.trainer.outclk_delay_inc),
            phy.halfswap.eq(self.trainer.halfswap),

            self.trainer.lane_match.eq(phy.lane_match),
            self.trainer.lane_mismatch.eq(phy.lane_mismatch),
        ]

        return m
