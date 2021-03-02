from nmigen import *
from . import AxiEndpoint

__all__ = ["if_none_get_zynq_hp_port"]


def if_none_get_zynq_hp_port(maybe_axi_port, m, platform) -> AxiEndpoint:
    """If `maybe_axi_port` is None, grab an AXI HP port from the zynq and return it. Otherwise returns the passed in AXI port."""
    if maybe_axi_port is not None:
        assert not maybe_axi_port.is_lite
        axi = maybe_axi_port
    else:
        clock_signal = Signal()
        m.d.comb += clock_signal.eq(ClockSignal())
        axi = platform.ps7.get_axi_hp_slave(clock_signal)
    return axi
