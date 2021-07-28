from nmigen import *
from .s7_phy import HostTrainer, Cmv12kPhy

__all__ = ["Cmv12kRx"]

class Cmv12kRx(Elaboratable):
    def __init__(self, sensor, num_lanes=32, bits=12, domain="cmv12k"):
        self.domain = domain
        self.lvds_outclk = sensor.lvds_outclk
        # NOTE: only two sided readout mode is supported
        assert num_lanes in (2, 4, 8, 16, 32, 64)
        # 32 lane mode uses every 2nd lane, 16 lane mode uses every 4th, etc...
        lane_nums = range(1, 65, 2**(7-num_lanes.bit_length()))
        self.lanes = Cat(getattr(sensor, f"lvds_{l}") for l in lane_nums)
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

            phy.lane_pattern.eq(trainer.lane_pattern),
            phy.lane_delay_reset.eq(trainer.lane_delay_reset),
            phy.lane_delay_inc.eq(trainer.lane_delay_inc),
            phy.lane_bitslip.eq(trainer.lane_bitslip),
            phy.outclk_delay_reset.eq(trainer.outclk_delay_reset),
            phy.outclk_delay_inc.eq(trainer.outclk_delay_inc),
            phy.halfslip.eq(trainer.halfslip),

            trainer.lane_match.eq(phy.lane_match),
            trainer.lane_mismatch.eq(phy.lane_mismatch),
        ]

        return m
