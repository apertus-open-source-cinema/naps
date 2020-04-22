from nmigen import *

from modules.axi.axi import AxiInterface
from modules.axi.axil_reg import AxiLiteReg
from util.nmigen import connect_together


class AxiInterconnect(Elaboratable):
    def __init__(self, uplink_axi_master):
        """
        A simple single master to many slaves AXI interconnect.

        :type uplink_axi_master: AxiInterface
        :param uplink_axi_master: The axi master to which the inteconnect is connected.
        """
        self._uplink_axi_master = uplink_axi_master
        assert uplink_axi_master.is_lite, "AXI interconnect only supports AXI lite atm"
        self._downstream_ports = []
        self._peripherals_module = Module()

    def get_port(self):
        """
        Gets a AXI master port connected to the master via this interconnect.

        :return: A new AxiInterface shaped after the upstream port.
        """
        downstream_master = AxiInterface.like(self._uplink_axi_master)
        self._downstream_ports.append(downstream_master)
        return downstream_master

    def peripheral_on_interconnect(self, peripheral, module=None):
        """
        A helper function to create a Peripheral, that is connected to a new port of an AXI interconnect.

        usage example:
        >>> csr = interconnect.peripheral_on_interconnect(AxiLiteReg(...), m)

        :param peripheral: the peripheral to add to the interconnect. Assumes the peripheral exposes its axi interface via peripheral.bus
        :param module: (optional) a module to add the peripheral to as a submodule instead of using the interconnect module.
        """
        assert hasattr(peripheral, "bus") and isinstance(peripheral.bus, AxiInterface), "The peripheral should expose its axi interface via peripheral.bus"

        if module is None:
            m = self._peripherals_module
        else:
            m = module

        m.submodules += peripheral
        m.d.comb += self.get_port().connect_slave(peripheral.bus)

        return peripheral

    def elaborate(self, platform):
        m = Module()

        # beware: the following only works for axi lite!
        for downstream_port in self._downstream_ports:
            def a(**kwargs):
                assert len(kwargs.keys()) == 1
                name, signal = list(kwargs.items())[0]
                return connect_together(signal, "{}2{}_{}".format(repr(self), repr(downstream_port), name), operation='&')

            uplink = self._uplink_axi_master
            m.d.comb += downstream_port.read_address.value.eq(uplink.read_address.value)
            m.d.comb += downstream_port.read_address.valid.eq(uplink.read_address.valid)
            m.d.comb += uplink.read_address.ready.eq(a(rar=downstream_port.read_address.ready))

            with m.If(downstream_port.read_data.valid):
                m.d.comb += uplink.read_data.value.eq(downstream_port.read_data.value)
                m.d.comb += uplink.read_data.valid.eq(downstream_port.read_data.valid)
                m.d.comb += uplink.read_data.resp.eq(downstream_port.read_data.resp)
                m.d.comb += downstream_port.read_data.ready.eq(uplink.read_data.ready)

            m.d.comb += downstream_port.write_address.value.eq(uplink.write_address.value)
            m.d.comb += downstream_port.write_address.valid.eq(uplink.write_address.valid)
            m.d.comb += uplink.write_address.ready.eq(a(war=downstream_port.write_address.ready))

            with m.If(downstream_port.write_data.valid):
                m.d.comb += downstream_port.write_data.value.eq(uplink.write_data.value)
                m.d.comb += downstream_port.write_data.valid.eq(uplink.write_data.valid)
                m.d.comb += downstream_port.write_data.strb.eq(uplink.write_data.strb)
                m.d.comb += uplink.write_data.ready.eq(downstream_port.write_data.ready)

            with m.If(downstream_port.write_response.valid):
                m.d.comb += uplink.write_response.resp.eq(downstream_port.write_response.resp)
                m.d.comb += uplink.write_response.valid.eq(downstream_port.write_response.valid)
                m.d.comb += downstream_port.write_response.ready.eq(uplink.write_response.ready)

        m.submodules["peripherals"] = self._peripherals_module

        return m
