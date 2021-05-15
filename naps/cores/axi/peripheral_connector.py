from nmigen import *

from .axi_endpoint import AxiResponse as AxiResponse, AxiEndpoint
from naps.soc.peripheral import Response as BusSlaveResponse, Peripheral

__all__ = ["AxiLitePeripheralConnector"]


class AxiLitePeripheralConnector(Elaboratable):
    def __init__(self, peripheral: Peripheral, bundle_name="axi", timeout=1000):
        """
        A simple (low performance) axi lite `PeripheralConnector` for connecting `Peripheral`s to an AXI Lite Bus.
        :param peripheral: The peripheral which this controller should handle
        :param timeout: the timeout after which an unsuccessful read attempt should fail (useful for not hanging everything)
        """
        assert callable(peripheral.handle_read) and callable(peripheral.handle_write)
        self.peripheral = peripheral
        self.timeout = timeout

        self.axi = AxiEndpoint(addr_bits=32, data_bits=32, lite=True, name=bundle_name)

    def elaborate(self, platform):
        m = Module()

        address_range = self.peripheral.range()

        assert address_range is not None
        assert address_range.start < address_range.stop

        addr = Signal.like(self.axi.read_address.payload)
        read_out = Signal.like(self.axi.read_data.payload)
        resp_out = Signal.like(self.axi.read_data.resp)

        read_write_done = Signal()
        timeout_counter = Signal(range(self.timeout + 1))

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

                with m.If(self.axi.read_address.valid & in_range(self.axi.read_address.payload)):
                    m.next = "FETCH_READ_ADDRESS"
                with m.Elif(self.axi.write_address.valid & in_range(self.axi.write_address.payload)):
                    m.next = "FETCH_WRITE_ADDRESS"

            with m.State("FETCH_READ_ADDRESS"):
                m.d.sync += addr.eq(self.axi.read_address.payload - address_range.start)
                m.d.comb += self.axi.read_address.ready.eq(1)
                m.next = "READ"
                m.d.sync += timeout_counter.eq(0)
            with m.State("READ"):
                # Only write read and resp if we are in the READ state. Otherwise all bits are '0'.
                # This allows us to simply or the data output of multiple axi slaves together.
                with m.If(read_write_done):
                    m.d.sync += read_write_done.eq(0)
                    m.next = "READ_DONE"
                with m.Else():
                    m.d.sync += timeout_counter.eq(timeout_counter + 1)
                    self.peripheral.handle_read(m, addr, read_out, read_write_done_callback)
                with m.If(timeout_counter == self.timeout):
                    m.d.sync += read_write_done.eq(1)
                    m.d.sync += resp_out.eq(AxiResponse.DECERR)
            with m.State("READ_DONE"):
                m.d.comb += self.axi.read_data.payload.eq(read_out)
                m.d.comb += self.axi.read_data.resp.eq(resp_out)
                m.d.comb += self.axi.read_data.valid.eq(1)
                with m.If(self.axi.read_data.ready):
                    m.next = "IDLE"

            with m.State("FETCH_WRITE_ADDRESS"):
                m.d.sync += addr.eq(self.axi.write_address.payload - address_range.start)
                m.d.comb += self.axi.write_address.ready.eq(1)
                m.next = "WRITE"
                m.d.sync += timeout_counter.eq(0)
            with m.State("WRITE"):
                with m.If(self.axi.write_data.valid):
                    with m.If(read_write_done):
                        m.d.sync += read_write_done.eq(0)
                        m.next = "WRITE_DONE"
                    with m.Else():
                        self.peripheral.handle_write(m, addr, self.axi.write_data.payload, read_write_done_callback)
                        m.d.sync += timeout_counter.eq(timeout_counter + 1)
                    with m.If(timeout_counter == self.timeout):
                        m.d.sync += read_write_done.eq(1)
                        m.d.sync += resp_out.eq(AxiResponse.DECERR)
            with m.State("WRITE_DONE"):
                m.d.comb += self.axi.write_response.resp.eq(resp_out)
                m.d.comb += self.axi.write_response.valid.eq(1)
                m.d.comb += self.axi.write_data.ready.eq(1)
                with m.If(self.axi.write_response.ready):
                    m.next = "IDLE"

        return m
