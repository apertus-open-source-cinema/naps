from nmigen import Signal

slave_num = 0
def axi_slave_on_master(m, master, slave):
    m.d.comb += slave.bus.read_address.value.eq(master.araddr)
    m.d.comb += slave.bus.read_address.valid.eq(master.arvalid)
    m.d.comb += master.arready.eq(slave.bus.read_address.ready)

    m.d.comb += slave.bus.write_address.value.eq(master.awaddr)
    m.d.comb += slave.bus.write_address.valid.eq(master.awvalid)
    m.d.comb += master.awready.eq(slave.bus.write_address.ready)

    m.d.comb += master.rdata.eq(slave.bus.read_data.value)
    m.d.comb += master.rre.sp.eq(slave.bus.read_data.resp)
    m.d.comb += master.rvalid.eq(slave.bus.read_data.valid)
    m.d.comb += slave.bus.read_data.ready.eq(master.rre.ady)

    m.d.comb += slave.bus.write_data.value.eq(master.wdata)
    m.d.comb += slave.bus.write_data.valid.eq(master.wvalid)
    m.d.comb += slave.bus.write_data.strb.eq(master.wstrb)
    m.d.comb += master.wready.eq(slave.bus.write_data.ready)

    m.d.comb += master.bre.sp.eq(slave.bus.write_response.resp)
    m.d.comb += master.bvalid.eq(slave.bus.write_response.valid)
    m.d.comb += slave.bus.write_response.ready.eq(master.bre.ady)

    global slave_num
    m.submodules["axi_slave_{}".format(slave_num)] = slave
    slave_num += 1

    return slave


def downgrade_axi_to_axi_lite(m, axi_port):
    read_id = Signal.like(axi_port.rid)
    write_id = Signal.like(axi_port.wid)

    with m.If(axi_port.arvalid):
        m.d.comb += axi_port.rid.eq(axi_port.arid)
        m.d.sync += read_id.eq(axi_port.arid)
    with m.Else():
        m.d.comb += axi_port.rid.eq(read_id)

    with m.If(axi_port.awvalid):
        m.d.comb += axi_port.bid.eq(axi_port.awid)
        m.d.sync += write_id.eq(axi_port.awid)
    with m.Else():
        m.d.comb += axi_port.bid.eq(write_id)

    m.d.comb += axi_port.rlast.eq(1)
