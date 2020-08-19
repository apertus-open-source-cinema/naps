from nmigen import *

from cores.axi.axi_endpoint import Response as AxiResponse, AxiEndpoint
from soc.peripheral import Response as BusSlaveResponse, Peripheral


class AxiLitePeripheralConnector(Elaboratable):
    def __init__(self, peripheral: Peripheral, bundle_name="axi"):
        """
        A simple (low performance) axi lite `PeripheralConnector` for connecting `Peripheral`s to an AXI Lite Bus.
        :param peripheral: The peripheral which this controller should handle
        """
        assert callable(peripheral.handle_read) and callable(peripheral.handle_write)
        self.peripheral = peripheral

        self.axi = AxiEndpoint(master=False, addr_bits=32, data_bits=32, lite=True, name=bundle_name)

    def elaborate(self, platform):
        m = Module()

        address_range = self.peripheral.range()

        assert address_range is not None
        assert address_range.start < address_range.stop

        addr = Signal.like(self.axi.read_address.value)
        read_out = Signal.like(self.axi.read_data.value)
        resp_out = Signal.like(self.axi.read_data.resp)

        read_write_done = Signal()

        def read_write_done_callback(error):
            m.d.sync += read_write_done.eq(1)
            if error == BusSlaveResponse.ERR:
                m.d.sync += resp_out.eq(AxiResponse.SLVERR)
            else:
                m.d.sync += resp_out.eq(AxiResponse.OKAY)

        with m.FSM():
            with m.State("IDLE"):
                def in_range(signal):
                    return (signal >= address_range.start) & (signal < address_range.stop)

                with m.If(self.axi.read_address.valid & in_range(self.axi.read_address.value)):
                    m.next = "FETCH_READ_ADDRESS"
                with m.Elif(self.axi.write_address.valid & in_range(self.axi.write_address.value)):
                    m.next = "FETCH_WRITE_ADDRESS"

            with m.State("FETCH_READ_ADDRESS"):
                m.d.sync += addr.eq(self.axi.read_address.value - address_range.start)
                m.d.comb += self.axi.read_address.ready.eq(1)
                m.next = "READ"
            with m.State("READ"):
                # Only write read and resp if we are in the READ state. Otherwise all bits are '0'.
                # This allows us to simply or the data output of multiple axi slaves together.

                self.peripheral.handle_read(m, addr, read_out, read_write_done_callback)
                with m.If(read_write_done):
                    m.d.sync += read_write_done.eq(0)
                    m.next = "READ_DONE"
            with m.State("READ_DONE"):
                m.d.comb += self.axi.read_data.value.eq(read_out)
                m.d.comb += self.axi.read_data.resp.eq(resp_out)
                m.d.comb += self.axi.read_data.valid.eq(1)
                with m.If(self.axi.read_data.ready):
                    m.next = "IDLE"

            with m.State("FETCH_WRITE_ADDRESS"):
                m.d.sync += addr.eq(self.axi.write_address.value - address_range.start)
                m.d.comb += self.axi.write_address.ready.eq(1)
                m.next = "WRITE"
            with m.State("WRITE"):
                with m.If(self.axi.write_data.valid):
                    self.peripheral.handle_write(m, addr, self.axi.write_data.value, read_write_done_callback)
                    with m.If(read_write_done):
                        m.d.sync += read_write_done.eq(0)
                        m.next = "WRITE_DONE"
            with m.State("WRITE_DONE"):
                m.d.comb += self.axi.write_response.resp.eq(resp_out)
                m.d.comb += self.axi.write_response.valid.eq(1)
                m.d.comb += self.axi.write_data.ready.eq(1)
                with m.If(self.axi.write_response.ready):
                    m.next = "IDLE"

        return m
