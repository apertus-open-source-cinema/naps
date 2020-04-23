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

        m.d.comb += [lite_master.read_address.value.eq(full_slave.read_address.value)]
        m.d.comb += [lite_master.read_address.valid.eq(full_slave.read_address.valid)]
        m.d.comb += [full_slave.read_address.ready.eq(lite_master.read_address.ready)]

        m.d.comb += [full_slave.read_data.value.eq(lite_master.read_data.value)]
        m.d.comb += [full_slave.read_data.valid.eq(lite_master.read_data.valid)]
        m.d.comb += [full_slave.read_data.resp.eq(lite_master.read_data.resp)]
        m.d.comb += [lite_master.read_data.ready.eq(full_slave.read_data.ready)]

        m.d.comb += [lite_master.write_address.value.eq(full_slave.write_address.value)]
        m.d.comb += [lite_master.write_address.valid.eq(full_slave.write_address.valid)]
        m.d.comb += [full_slave.write_address.ready.eq(lite_master.write_address.ready)]

        m.d.comb += [lite_master.write_data.value.eq(full_slave.write_data.value)]
        m.d.comb += [lite_master.write_data.valid.eq(full_slave.write_data.valid)]
        m.d.comb += [lite_master.write_data.strb.eq(full_slave.write_data.strb)]
        m.d.comb += [full_slave.write_data.ready.eq(lite_master.write_data.ready)]

        m.d.comb += [full_slave.write_response.resp.eq(lite_master.write_response.resp)]
        m.d.comb += [full_slave.write_response.valid.eq(lite_master.write_response.valid)]
        m.d.comb += [lite_master.write_response.ready.eq(full_slave.write_response.ready)]

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
