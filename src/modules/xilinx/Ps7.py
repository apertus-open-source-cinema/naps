from modules.axi.axi import AxiInterface
import modules.xilinx.blocks as blocks


class Ps7(blocks.Ps7):
    def _to_axi_helper(self, axi, ps7_port):
        # replacing the Signals from the original interface is a bit ugly but works since we have just created it
        # and are therefore sure, that there are no other references to them
        axi.read_address.value = ps7_port.araddr
        axi.read_address.valid = ps7_port.arvalid
        axi.read_address.ready = ps7_port.arready
        axi.read_address.id = ps7_port.arid
        axi.read_address.burst_type = ps7_port.arburst
        axi.read_address.burst_len = ps7_port.arl.en
        axi.read_address.beat_size_bytes = ps7_port.arsize
        axi.read_address.protection_type = ps7_port.arprot
        axi.read_data.value = ps7_port.rdata
        axi.read_data.resp = ps7_port.rre.sp
        axi.read_data.valid = ps7_port.rvalid
        axi.read_data.ready = ps7_port.rre.ady
        axi.read_data.id = ps7_port.rid
        axi.read_data.last = ps7_port.rlast
        axi.write_address.value = ps7_port.awaddr
        axi.write_address.valid = ps7_port.awvalid
        axi.write_address.ready = ps7_port.awready
        axi.write_address.id = ps7_port.awid
        axi.write_address.burst_type = ps7_port.awburst
        axi.write_address.burst_len = ps7_port.awl.en
        axi.write_address.beat_size_bytes = ps7_port.awsize
        axi.write_address.protection_type = ps7_port.awprot
        axi.write_data.value = ps7_port.wdata
        axi.write_data.valid = ps7_port.wvalid
        axi.write_data.byte_strobe = ps7_port.wstrb
        axi.write_data.ready = ps7_port.wready
        axi.write_data.id = ps7_port.wid
        axi.write_data.last = ps7_port.wlast
        axi.write_response.resp = ps7_port.bre.sp
        axi.write_response.valid = ps7_port.bvalid
        axi.write_response.ready = ps7_port.bre.ady
        axi.write_response.id = ps7_port.bid

    def get_axi_gp_master(self, number) -> AxiInterface:
        axi = AxiInterface(addr_bits=32, data_bits=32, lite=False, id_bits=0, master=True)

        ps7_port = self.maxigp[number]
        self._to_axi_helper(axi, ps7_port)

        return axi

    def get_axi_hp_slave(self, number) -> AxiInterface:
        axi = AxiInterface(addr_bits=32, data_bits=32, lite=False, id_bits=4, master=False)

        ps7_port = self.saxi.hp[number]
        self._to_axi_helper(axi, ps7_port)

        return axi