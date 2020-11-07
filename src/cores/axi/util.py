from nmigen import Signal, ClockSignal

from cores.axi import AxiEndpoint


def get_axi_master_from_maybe_slave(axi_slave, m, platform):
    if axi_slave is not None:
        assert not axi_slave.is_lite
        assert not axi_slave.is_master
        axi_slave = axi_slave
    else:
        clock_signal = Signal()
        m.d.comb += clock_signal.eq(ClockSignal())
        axi_slave = platform.ps7.get_axi_hp_slave(clock_signal)
    axi = AxiEndpoint.like(axi_slave, master=True)
    m.d.comb += axi.connect_slave(axi_slave)
    return axi