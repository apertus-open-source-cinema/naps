from .xilinx_blackbox import XilinxBlackbox
from ..axi import axi
from ..axi.axi import AxiInterface


class Ps7(XilinxBlackbox):
    module = "PS7"

    def get_axi_master_gp(self, number) -> AxiInterface:
        bus = axi.AxiInterface(addr_bits=32, data_bits=32, lite=False, id_bits=4, master=True)
        ps7_port = self.maxigp[number]
        # replacing the Signals from the original interface is a bit ugly but works since we have just created it
        # and are therefore sure, that there are no other references to them
        bus.read_address.value = ps7_port.araddr
        bus.read_address.valid = ps7_port.arvalid
        bus.read_address.ready = ps7_port.arready

        bus.read_data.value = ps7_port.rdata
        bus.read_data.resp = ps7_port.rre.sp
        bus.read_data.valid = ps7_port.rvalid
        bus.read_data.ready = ps7_port.rre.ady

        bus.write_address.value = ps7_port.awaddr
        bus.write_address.valid = ps7_port.awvalid
        bus.write_address.ready = ps7_port.awready

        bus.write_data.value = ps7_port.wdata
        bus.write_data.valid = ps7_port.wvalid
        bus.write_data.strb = ps7_port.wstrb
        bus.write_data.ready = ps7_port.wready

        bus.write_response.value = ps7_port.bre.sp
        bus.write_response.valid = ps7_port.bvalid
        bus.write_response.ready = ps7_port.bre.ady

        return bus


class Oserdes(XilinxBlackbox):
    module = "OSERDESE2"


class Iserdes(XilinxBlackbox):
    module = "ISERDESE2"


class Idelay(XilinxBlackbox):
    module = "IDELAYE2"


class IdelayCtl(XilinxBlackbox):
    module = "IDELAYCTRL"


class RawPll(XilinxBlackbox):
    module = "PLLE2_BASE"


class Bufg(XilinxBlackbox):
    module = "BUFG"
