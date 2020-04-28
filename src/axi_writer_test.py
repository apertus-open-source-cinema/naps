from nmigen import *
from nmigen.build import Resource, Subsignal, DiffPairs, Attrs

from modules.axi.axi import AxiInterface
from modules.axi.axi_writer import AxiHpWriter
from modules.axi.axil_csr import AxilCsrBank
from modules.axi.full_to_lite import AxiFullToLiteBridge
from modules.xilinx.Ps7 import Ps7
from modules.xilinx.blocks import Oserdes, RawPll, Bufg, Idelay, IdelayCtl, Iserdes
from devices.micro.micro_r2_platform import MicroR2Platform


class Top(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, plat: MicroR2Platform):
        m = self.module = Module()

        m.domains += ClockDomain("sync")
        ps7 = m.submodules.ps7_wrapper = Ps7()
        m.d.comb += ClockSignal().eq(ps7.fclk.clk[0])

        axi_full_port: AxiInterface = ps7.get_axi_gp_master(0, ClockSignal())
        axi_lite_bridge = m.submodules.axi_lite_bridge = AxiFullToLiteBridge(axi_full_port)
        csr = m.submodules.csr = AxilCsrBank(axi_lite_bridge.lite_master)

        axi_hp_port = ps7.get_axi_hp_slave(1, ClockSignal())
        axi_writer = m.submodules.axi_writer = AxiHpWriter(axi_hp_port, [0x0f80_0000], max_buffer_size=0x0001_0000)
        m.d.comb += csr.csr_for_module(axi_writer, "axi_writer", inputs=["change_buffer", "data_valid"],
                                       outputs=["error", "dropped", "data_ready", "state", "written", "burst_position"],
                                       data_valid=0)

        m.d.comb += csr.reg("axi__write_address__ready", writable=False).eq(axi_hp_port.write_address.ready)
        m.d.comb += csr.reg("axi__write_data__ready", writable=False).eq(axi_hp_port.write_data.ready)

        counter = csr.reg("counter", writable=False)
        with m.If(axi_writer.data_ready & axi_writer.data_valid):
            m.d.sync += counter.eq(counter + 1)
        m.d.comb += axi_writer.data.eq(Cat(counter, counter+1000))

        return m


if __name__ == "__main__":
    p = MicroR2Platform()
    top = Top()

    # print_module_sizes(top, platform=p)
    from util.draw_hierarchy import hierarchy_to_dot

    # with open("test.json", "w") as f:
    #    f.write(hierarchy_to_dot(top, p))
    p.build(
        top,
        name=__file__.split(".")[0].split("/")[-1],
        do_build=True,
        do_program=True,
        program_opts={"host": "micro"}
    )
