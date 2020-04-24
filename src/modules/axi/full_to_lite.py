from nmigen import *

from modules.axi.axi import AxiInterface


class AxiFullToLiteBridge(Elaboratable):
    def __init__(self, full_master: AxiInterface):
        assert full_master.is_master and not full_master.is_lite
        self._full_master = full_master
        self.lite_master = AxiInterface.like(full_master, lite=True)

    def elaborate(self, platform):
        m = Module()

        full_slave = AxiInterface.like(self._full_master, master=False)
        m.d.comb += self._full_master.connect_slave(full_slave)

        lite_master = self.lite_master

        m.d.comb += [
            lite_master.read_address.value.eq(full_slave.read_address.value),
            lite_master.read_address.valid.eq(full_slave.read_address.valid),
            full_slave.read_address.ready.eq(lite_master.read_address.ready),

            full_slave.read_data.value.eq(lite_master.read_data.value),
            full_slave.read_data.valid.eq(lite_master.read_data.valid),
            full_slave.read_data.resp.eq(lite_master.read_data.resp),
            lite_master.read_data.ready.eq(full_slave.read_data.ready),

            lite_master.write_address.value.eq(full_slave.write_address.value),
            lite_master.write_address.valid.eq(full_slave.write_address.valid),
            full_slave.write_address.ready.eq(lite_master.write_address.ready),

            lite_master.write_data.value.eq(full_slave.write_data.value),
            lite_master.write_data.valid.eq(full_slave.write_data.valid),
            lite_master.write_data.byte_strobe.eq(full_slave.write_data.byte_strobe),
            full_slave.write_data.ready.eq(lite_master.write_data.ready),

            full_slave.write_response.resp.eq(lite_master.write_response.resp),
            full_slave.write_response.valid.eq(lite_master.write_response.valid),
            lite_master.write_response.ready.eq(full_slave.write_response.ready),
        ]

        # fake the id tracking
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
