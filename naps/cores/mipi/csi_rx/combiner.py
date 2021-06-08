from typing import List
from nmigen import *
from nmigen.lib.io import Pin
from naps import PacketizedFirstStream, nAny, nAll
from naps.cores import StreamGearbox

from .s7_rx_phy import MipiClockRxPhy
from .aligner import CsiWordAligner

__all__ = ["CsiLaneCombiner"]


class CsiLaneCombiner(Elaboratable):
    """
    Combines 1 to 4 lanes to a 32 bit word that can be used for parsing the packet header.
    Also assists with the training of multiple lanes.
    """

    def __init__(self, clock_pin: Pin, data_pins: List[Pin], domain_prefix="mipi"):
        self.domain_prefix = domain_prefix
        self.clock_pin = clock_pin
        self.data_pins = data_pins

        self.in_packet = Signal()  # input; indicates if the upper layer is in a valid packet
        self.output = PacketizedFirstStream(32)

    def elaborate(self, platform):
        m = Module()

        word_domain = f'{self.domain_prefix}_word'
        ddr_domain = f'{self.domain_prefix}_ddr'

        clock_phy = m.submodules.clock_phy = MipiClockRxPhy(self.clock_pin, ddr_domain)
        lane_phys = [CsiWordAligner(pin, ddr_domain, self.in_packet) for pin in self.data_pins]
        for i, phy in enumerate(lane_phys):
            m.submodules[f'lane_{i + 1}_phy'] = phy

        # training of multiple lanes:
        # if some (but not all) lanes assert maybe_first_packet_byte we disable the training logic for the ones that asserted maybe_first_packet_byte
        # and let the others continue their Training. This however can lead to endless loops (when some lane is trained on not the sync pattern but some
        # other piece of data). To reduce the likeliness that this happens we only re-enable the training logic if the training did not work after a timeout
        # (measured in assertions of maybe_first_packet_byte)
        timeout = 27
        timeout_ctr = Signal(range(timeout))

        def reset_successive_training():
            m.d.sync += timeout_ctr.eq(0)
            for l in lane_phys:
                m.d.sync += l.enable_train_logic.eq(1)

        mfpb = [l.maybe_first_packet_byte for l in lane_phys]
        with m.If(~self.in_packet & nAll(mfpb)):  # we completed training successfully
            reset_successive_training()
        with m.Elif(~self.in_packet & nAny(mfpb) & ~nAll(l.maybe_first_packet_byte | l.enable_train_logic for l in lane_phys)):  # we are certainly not on the right path
            reset_successive_training()
        with m.Elif(~self.in_packet & nAny(mfpb) & (timeout_ctr < timeout)):
            m.d.sync += timeout_ctr.eq(timeout_ctr + 1)
            for l in lane_phys:
                with m.If(l.maybe_first_packet_byte & nAny(l.maybe_first_packet_byte & ~l.enable_train_logic for l in lane_phys)):
                    m.d.sync += l.enable_train_logic.eq(0)
        with m.Elif(~self.in_packet & nAny(mfpb)):
            reset_successive_training()

        gearbox_input = PacketizedFirstStream(8 * len(lane_phys))
        m.d.comb += gearbox_input.first.eq(nAll(mfpb))
        for i, l in enumerate(lane_phys):
            m.d.comb += gearbox_input.payload[i * 8: (i + 1) * 8].eq(l.output)
        gearbox = m.submodules.gearbox = StreamGearbox(gearbox_input, target_width=32)
        m.d.comb += self.output.connect_upstream(gearbox.output)

        return m
