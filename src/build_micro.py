from nmigen import *
from modules.axi.axil_reg import AxiLiteReg
from modules.xilinx.blocks import Ps7
from devices.micro.micro_r2_platform import MicroR2Platform


class Top(Elaboratable):
    def __init__(self):
        pass
        # reduced_layout = [("a", 8, Direction.FANIN), ("b", 12, Direction.FANOUT)]
        # full_layout = [*reduced_layout, ("c", 8, Direction.FANIN)]
        # self.a = Record(full_layout)
        # self.b = Record(reduced_layout)

    def elaborate(self, plat):
        m = Module()

        m.domains += ClockDomain("sync")
        ps7 = m.submodules.ps7_wrapper = Ps7()

        m.submodules.axi_reg = reg = AxiLiteReg(width=8, base_address=0x4000_0000)
        # print(reg.bus)
        # print(ps7.maxigp[0].hierarchy)

        axi_port = ps7.maxigp[0]

        m.d.comb += ClockSignal().eq(ps7.fclk.clk[0])
        m.d.comb += axi_port.aclk.eq(ClockSignal())
        m.d.comb += ResetSignal().eq(~axi_port.aresetn)
        m.d.comb += reg.axi.read_address.value.eq(axi_port.araddr)
        m.d.comb += reg.axi.read_address.valid.eq(axi_port.arvalid)
        m.d.comb += axi_port.arready.eq(reg.axi.read_address.ready)

        m.d.comb += reg.axi.write_address.value.eq(axi_port.awaddr)
        m.d.comb += reg.axi.write_address.valid.eq(axi_port.awvalid)
        m.d.comb += axi_port.awready.eq(reg.axi.write_address.ready)

        m.d.comb += axi_port.rdata.eq(reg.axi.read_data.value)
        m.d.comb += axi_port.rre.sp.eq(reg.axi.read_data.resp)
        m.d.comb += axi_port.rvalid.eq(reg.axi.read_data.valid)
        m.d.comb += reg.axi.read_data.ready.eq(axi_port.rre.ady)

        m.d.comb += reg.axi.write_data.value.eq(axi_port.wdata)
        m.d.comb += reg.axi.write_data.valid.eq(axi_port.wvalid)
        m.d.comb += reg.axi.write_data.byte_strobe.eq(axi_port.wstrb)
        m.d.comb += axi_port.wready.eq(reg.axi.write_data.ready)

        m.d.comb += axi_port.bre.sp.eq(reg.axi.write_response.resp)
        m.d.comb += axi_port.bvalid.eq(reg.axi.write_response.valid)
        m.d.comb += reg.axi.write_response.ready.eq(axi_port.bre.ady)

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

        # m.d.comb += reg.bus.
        # m.d.comb += self.a.a.eq(self.a.b)
        # m.d.comb += self.a.connect(self.b, exclude = {"c"})

        return m


if __name__ == "__main__":
    # dut = Top()
    # print(verilog.convert(dut))

    p = MicroR2Platform()
    p.build(Top(), do_build=True)
