import math

from nmigen import *

from modules.axi.axi import AxiInterface
from modules.axi.buffer_writer import AxiBufferWriter
from modules.axi.csr_auto import AutoCsrBank
from modules.axi.full_to_lite import AxiFullToLiteBridge
from devices.micro.micro_r2_platform import MicroR2Platform


class Top(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, plat: MicroR2Platform):
        m = self.module = Module()

        ps7 = plat.get_ps7()

        ps7.fck_domain("axi_csr", requested_frequency=100e6)
        axi_full_port: AxiInterface = ps7.get_axi_gp_master(0, ClockSignal("axi_csr"))
        axi_lite_bridge = m.submodules.axi_lite_bridge = DomainRenamer("axi_csr")(AxiFullToLiteBridge(axi_full_port))
        csr = m.submodules.csr = DomainRenamer("axi_csr")(AutoCsrBank(axi_lite_bridge.lite_master))

        ps7.fck_domain(requested_frequency=200e6)
        m.d.comb += ResetSignal().eq(csr.reg("reset", width=1))

        axi_hp_port = ps7.get_axi_hp_slave(1, ClockSignal())
        to_write = csr.reg("to_write", reset=32 * 1024 * 1024)
        axi_writer = m.submodules.axi_writer = AxiBufferWriter(axi_hp_port, [0x0f80_0000], max_buffer_size=to_write, max_burst_length=16)
        csr.csr_for_module(axi_writer, "axi_writer")

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

    p.build(
        Top(),
        name=__file__.split(".")[0].split("/")[-1],
        do_build=True,
        do_program=True,
        program_opts={"host": "micro"}
    )