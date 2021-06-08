from nmigen import *

from .s7_rx_phy import MipiLaneRxPhy

__all__ = ["CsiWordAligner"]


class CsiWordAligner(Elaboratable):
    """A timeout based word aligner. Issues a bitslip request to the PHY if for a specified time no valid packet (as indicated by a upper layer) was received."""

    def __init__(self, pin, ddr_domain, in_packet, timeout=100_000, timeouts_to_retrain=1_000):
        self.timeouts_to_retrain = timeouts_to_retrain
        self.timeout = timeout
        self.ddr_domain = ddr_domain
        self.pin = pin

        self.enable_train_logic = Signal(reset=1)  # input; enables or disables the train logic; this is needed in multi lane setups to be able to find a training for all lanes
        self.in_packet = in_packet  # input; indicates if the upper layer is in a valid packet
        self.output = Signal(8)  # output
        self.maybe_first_packet_byte = Signal()  # indicates, that the current output word was preceded by the start of packet preamble

    def elaborate(self, platform):
        m = Module()

        phy = m.submodules.phy = MipiLaneRxPhy(self.pin, self.ddr_domain)
        m.d.comb += self.output.eq(phy.output)

        # the spec says ‘00011101’ but we need to reverse this here because we are receiving a lsb first stream
        start_of_packet = 0b10111000
        m.d.sync += self.maybe_first_packet_byte.eq((self.output == start_of_packet) & ~self.in_packet)

        with m.If(self.enable_train_logic):
            with m.FSM():
                timeout_counter = Signal(range(self.timeout))
                with m.State("UNALIGNED"):
                    with m.If(self.in_packet):
                        m.d.sync += timeout_counter.eq(0)
                        m.next = "ALIGNED"
                    with m.Elif(timeout_counter < self.timeout):
                        m.d.sync += timeout_counter.eq(timeout_counter + 1)
                    with m.Else():
                        m.d.comb += phy.bitslip.eq(1)
                        m.d.sync += timeout_counter.eq(0)

                aligned_timeouts_counter = Signal(range(self.timeouts_to_retrain))
                with m.State("ALIGNED"):
                    with m.If(self.in_packet):
                        m.d.sync += timeout_counter.eq(0)
                    with m.Elif(timeout_counter < self.timeout):
                        m.d.sync += timeout_counter.eq(timeout_counter + 1)
                    with m.Elif(aligned_timeouts_counter < self.timeouts_to_retrain):
                        m.d.sync += aligned_timeouts_counter.eq(aligned_timeouts_counter + 1)
                    with m.Else():
                        m.next = "UNALIGNED"

        return m
