from collections import defaultdict
from functools import reduce

from nmigen import Signal

slave_num = 0


def or_together(signal, name, internal_dict=defaultdict(list)):
    internal_dict[name].append(signal)
    return reduce(lambda acc, cur: acc | cur, internal_dict[name], Signal())


def axi_slave_on_master(m, master, slave):
    m.d.comb += slave.bus.read_address.value.eq(master.araddr)
    m.d.comb += slave.bus.read_address.valid.eq(master.arvalid)
    m.d.comb += master.arready.eq(or_together(slave.bus.read_address.ready, "arready"))

    m.d.comb += slave.bus.write_address.value.eq(master.awaddr)
    m.d.comb += slave.bus.write_address.valid.eq(master.awvalid)
    m.d.comb += master.awready.eq(or_together(slave.bus.write_address.ready, "awready"))

    m.d.comb += master.rdata.eq(or_together(slave.bus.read_data.value, "rdata"))
    m.d.comb += master.rre.sp.eq(or_together(slave.bus.read_data.resp, "rresp"))
    m.d.comb += master.rvalid.eq(or_together(slave.bus.read_data.valid, "rvalid"))
    m.d.comb += slave.bus.read_data.ready.eq(master.rre.ady)

    m.d.comb += slave.bus.write_data.value.eq(master.wdata)
    m.d.comb += slave.bus.write_data.valid.eq(master.wvalid)
    m.d.comb += slave.bus.write_data.strb.eq(master.wstrb)
    m.d.comb += master.wready.eq(or_together(slave.bus.write_data.ready, "wready"))

    m.d.comb += master.bre.sp.eq(or_together(slave.bus.write_response.resp, "bresp"))
    m.d.comb += master.bvalid.eq(or_together(slave.bus.write_response.valid, "bvalid"))
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
        m.d.axi += read_id.eq(axi_port.arid)
    with m.Else():
        m.d.comb += axi_port.rid.eq(read_id)

    with m.If(axi_port.awvalid):
        m.d.comb += axi_port.bid.eq(axi_port.awid)
        m.d.axi += write_id.eq(axi_port.awid)
    with m.Else():
        m.d.comb += axi_port.bid.eq(write_id)

    m.d.comb += axi_port.rlast.eq(1)
