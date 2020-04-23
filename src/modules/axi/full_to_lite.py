from nmigen import *

from modules.axi.axi import AxiInterface


class AxiFullToLiteBridge(Elaboratable):
    def __init__(self, full_master : AxiInterface):
        assert full_master.is_master and not full_master.is_lite
        self._full_master = full_master
        self.lite_master = AxiInterface.like(full_master, lite=True)

    def elaborate(self, platform):
        m = Module()

        full_slave = AxiInterface.like(self._full_master, master=False)
        m.d.comb += self._full_master.connect_slave(full_slave)

        read_id = Signal.like(full_slave.read_data.id)
        write_id = Signal.like(full_slave.write_data.id)

        with m.If(full_slave.read_address.valid):
            m.d.comb += full_slave.read_data.id.eq(full_slave.read_address.id)
            m.d.sync += read_id.eq(full_slave.read_address.id)
        with m.Else():
            m.d.comb += full_slave.read_data.id.eq(read_id)

        with m.If(full_slave.write_address.valid):
            m.d.comb += full_slave.write_data.id.eq(full_slave.write_address.id)
            m.d.sync += write_id.eq(full_slave.write_address.id)
        with m.Else():
            m.d.comb += full_slave.write_data.id.eq(write_id)

        m.d.comb += full_slave.read_data.last.eq(1)

        return m
