import math

from nmigen import *
from nmigen.build import Resource, Subsignal, DiffPairs, Attrs

from modules.axi.axi import AxiInterface
from modules.axi.axi_writer import AxiBufferWriter
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

        ps7 = m.submodules.ps7_wrapper = Ps7()
        ps7.fck_domain(frequency=200e6)

        m.domains += ClockDomain("axi_csr")  # we use another clockdomain here to be able to reset the other via axi
        m.d.comb += ClockSignal("axi_csr").eq(ClockSignal())
        axi_full_port: AxiInterface = ps7.get_axi_gp_master(0, ClockSignal("axi_csr"))
        axi_lite_bridge = m.submodules.axi_lite_bridge = DomainRenamer("axi_csr")(AxiFullToLiteBridge(axi_full_port))
        csr = m.submodules.csr = DomainRenamer("axi_csr")(AxilCsrBank(axi_lite_bridge.lite_master))

        m.d.comb += ResetSignal().eq(csr.reg("reset", width=1))

        axi_hp_port = ps7.get_axi_hp_slave(1, ClockSignal())
        to_write = csr.reg("to_write", reset=32 * 1024 * 1024)
        axi_writer = m.submodules.axi_writer = AxiBufferWriter(axi_hp_port, [0x0f80_0000], max_buffer_size=to_write, max_burst_length=16)
        m.d.comb += csr.csr_for_module(axi_writer, "axi_writer", inputs=["change_buffer", "data_valid"],
                                       outputs=["error", "dropped", "data_ready", "state", "written", "burst_position", "data_fifo_level", "address_fifo_level"],
                                       data_valid=0)

        m.d.comb += csr.reg("axi__write_address__ready", writable=False).eq(axi_hp_port.write_address.ready)
        m.d.comb += csr.reg("axi__write_data__ready", writable=False).eq(axi_hp_port.write_data.ready)

        data_counter = csr.reg("data_counter", writable=False)
        with m.If(axi_writer.data_ready & axi_writer.data_valid):
            m.d.sync += data_counter.eq(data_counter + 1)
        m.d.comb += axi_writer.data.eq(Cat(data_counter, data_counter+1000))

        perf_counter = csr.reg("perf_counter", writable=False)
        with m.If((axi_writer.data_valid) & (axi_writer.written < (to_write >> int(math.log2(axi_hp_port.data_bytes))))):
            m.d.sync += perf_counter.eq(perf_counter+1)

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
