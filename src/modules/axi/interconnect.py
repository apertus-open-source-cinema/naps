from functools import reduce

from nmigen import *

from modules.axi.axi import AxiInterface
from modules.axi.axil_reg import AxiLiteReg
from util.nmigen import connect_together, operator, iterator_with_if_elif


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

    def get_port(self):
        """
        Gets a AXI master port connected to the master via this interconnect.

        :return: A new AxiInterface shaped after the upstream port.
        """
        downstream_master = AxiInterface.like(self._uplink_axi_master)
        self._downstream_ports.append(downstream_master)
        return downstream_master

    def elaborate(self, platform):
        m = Module()

        # beware: the following works only for axi lite!

        uplink = self._uplink_axi_master

        for downstream_port in self._downstream_ports:
            m.d.comb += downstream_port.read_address.value.eq(uplink.read_address.value)
            m.d.comb += downstream_port.read_address.valid.eq(uplink.read_address.valid)
            m.d.comb += downstream_port.write_address.value.eq(uplink.write_address.value)
            m.d.comb += downstream_port.write_address.valid.eq(uplink.write_address.valid)

        # wait for _all_ peripherals when writing the addresses
        m.d.comb += uplink.read_address.ready.eq(reduce(lambda a, b: a & b, (d.read_address.ready for d in self._downstream_ports)))
        m.d.comb += uplink.write_address.ready.eq(reduce(lambda a, b: a & b, (d.write_address.ready for d in self._downstream_ports)))

        # we are creating priority encoders here: When multiple peripherals want to answer, we take the answer of the
        # first added peripheral
        for conditional, downstream_port in iterator_with_if_elif(self._downstream_ports, m):
            with conditional(downstream_port.read_data.valid):
                m.d.comb += uplink.read_data.value.eq(downstream_port.read_data.value)
                m.d.comb += uplink.read_data.valid.eq(downstream_port.read_data.valid)
                m.d.comb += uplink.read_data.resp.eq(downstream_port.read_data.resp)
                m.d.comb += downstream_port.read_data.ready.eq(uplink.read_data.ready)
        for conditional, downstream_port in iterator_with_if_elif(self._downstream_ports, m):
            with conditional(downstream_port.write_data.valid):
                m.d.comb += downstream_port.write_data.value.eq(uplink.write_data.value)
                m.d.comb += downstream_port.write_data.valid.eq(uplink.write_data.valid)
                m.d.comb += downstream_port.write_data.strb.eq(uplink.write_data.strb)
                m.d.comb += uplink.write_data.ready.eq(downstream_port.write_data.ready)
        for conditional, downstream_port in iterator_with_if_elif(self._downstream_ports, m):
            with conditional(downstream_port.write_response.valid):
                m.d.comb += uplink.write_response.resp.eq(downstream_port.write_response.resp)
                m.d.comb += uplink.write_response.valid.eq(downstream_port.write_response.valid)
                m.d.comb += downstream_port.write_response.ready.eq(uplink.write_response.ready)

        return m
