from typing import List
from nmigen import *
from naps.util.nmigen_misc import iterator_with_if_elif, nAny
from . import AxiEndpoint

__all__ = ["AxiInterconnect"]


class AxiInterconnect(Elaboratable):
    def __init__(self, upstream):
        """
        A simple single master to many slaves AXI interconnect.

        :type upstream: AxiEndpoint
        :param upstream: The axi master to which the interconnect is connected.
        """
        assert upstream.is_lite, "AXI interconnect only supports AXI lite atm"
        self._upstream = upstream
        self._downstream_ports: List[AxiEndpoint] = []

    def get_port(self):
        """
        Gets a AXI master port connected to the master via this interconnect.

        :return: A new AxiInterface shaped after the upstream port.
        """
        downstream_master = AxiEndpoint.like(self._upstream, name="axi_interconnect_downstream")
        self._downstream_ports.append(downstream_master)
        return downstream_master

    def elaborate(self, platform):
        m = Module()

        for downstream_port in self._downstream_ports:
            m.d.comb += downstream_port.read_address.connect_upstream(self._upstream.read_address)
            m.d.comb += downstream_port.write_address.connect_upstream(self._upstream.write_address)
            m.d.comb += downstream_port.write_data.connect_upstream(self._upstream.write_data)

        # wait until at least one peripherals is ready when writing the addresses
        m.d.comb += self._upstream.read_address.ready.eq(nAny(d.read_address.ready for d in self._downstream_ports))
        m.d.comb += self._upstream.write_address.ready.eq(nAny(d.write_address.ready for d in self._downstream_ports))

        # only one peripheral has to accept written data
        m.d.comb += self._upstream.write_data.ready.eq(nAny(d.write_data.ready for d in self._downstream_ports))

        # we are creating priority encoders here: When multiple peripherals want to answer, we take the answer of the
        # first added peripheral
        for conditional, downstream_port in iterator_with_if_elif(self._downstream_ports, m):
            with conditional(downstream_port.read_data.valid):
                m.d.comb += self._upstream.read_data.connect_upstream(downstream_port.read_data)
        for conditional, downstream_port in iterator_with_if_elif(self._downstream_ports, m):
            with conditional(downstream_port.write_response.valid):
                m.d.comb += self._upstream.write_response.connect_upstream(downstream_port.write_response)

        return m
