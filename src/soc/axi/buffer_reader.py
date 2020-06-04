# TODO: figure out api
# TODO: implement

from nmigen import *

from . import AxiInterface
from soc import ControlSignal, StatusSignal


class AxiBufferReader(Elaboratable):
    def __init__(self, axi_slave: AxiInterface, buffers_base_list):
        self._buffers_base_list = buffers_base_list
        self._axi_slave = axi_slave

        self.request = ControlSignal()
        self.ready = StatusSignal(axi_slave.data_bits)

    def elaborate(self, platform):
        m = Module()



        return m
