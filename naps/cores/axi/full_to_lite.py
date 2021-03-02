from nmigen import *
from . import AxiEndpoint

__all__ = ["AxiFullToLiteBridge"]


class AxiFullToLiteBridge(Elaboratable):
    def __init__(self, full_master: AxiEndpoint):
        assert not full_master.is_lite
        self._full_master = full_master
        self.lite_master = AxiEndpoint.like(full_master, lite=True, name="axi_lite_bridge_master")

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self._full_master.connect_downstream(self.lite_master, allow_partial=True)
        
        # fake the id tracking
        read_id = Signal.like(self._full_master.read_data.id)
        write_id = Signal.like(self._full_master.write_data.id)

        with m.If(self._full_master.read_address.valid):
            m.d.comb += self._full_master.read_data.id.eq(self._full_master.read_address.id)
            m.d.sync += read_id.eq(self._full_master.read_address.id)
        with m.Else():
            m.d.comb += self._full_master.read_data.id.eq(read_id)

        with m.If(self._full_master.write_address.valid):
            m.d.comb += self._full_master.write_response.id.eq(self._full_master.write_address.id)
            m.d.sync += write_id.eq(self._full_master.write_address.id)
        with m.Else():
            m.d.comb += self._full_master.write_response.id.eq(write_id)

        m.d.comb += self._full_master.read_data.last.eq(1)

        return m
