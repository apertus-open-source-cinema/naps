from nmigen import *
from nmigen.build import Platform

from naps import PacketizedStream, ControlSignal
from naps.cores import StreamSplitter
from .d_phy_lane import DPhyDataLane, DPhyClockLane


class DsiPhy(Elaboratable):
    def __init__(self, resource, num_lanes, ddr_domain):
        self.resource = resource
        self.num_lanes = num_lanes
        self.ddr_domain = ddr_domain

        self.control_input = PacketizedStream(8)
        self.control_output = PacketizedStream(8)
        self.hs_input = PacketizedStream(8 * num_lanes)
        self.request_hs = ControlSignal()


    def elaborate(self, platform: Platform):
        resource = platform.request(*self.resource, xdr={"hs_ck": 2, **{f"hs_d{i}": 2 for i in range(self.num_lanes)}})

        m = Module()

        lanes = []
        for i in range(2):
            lane = DPhyDataLane(
                lp_pins=getattr(resource, f"lp_d{i}"),
                hs_pins=getattr(resource, f"hs_d{i}"),
                is_lane_0=(i == 0),
                ddr_domain=self.ddr_domain
            )
            m.submodules[f"lane_d{i}"] = lane
            lanes.append(lane)

        lane0 = lanes[0]
        m.d.comb += lane0.control_input.connect_upstream(self.control_input)
        m.d.comb += self.control_output.connect_upstream(lane0.control_output)

        splitter = m.submodules.splitter = StreamSplitter(self.hs_input, self.num_lanes)
        for lane, hs_input in zip(lanes, splitter.outputs):
            m.d.comb += lane.hs_input.connect_upstream(hs_input)

        lane_ck = m.submodules.lane_ck = DPhyClockLane(resource.lp_ck, resource.hs_ck, ddr_domain=self.ddr_domain + "_90")
        m.d.comb += lane_ck.request_hs.eq(self.request_hs)

        return m
