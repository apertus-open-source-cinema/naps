from nmigen import *

from modules.axi.axi import Response
from modules.axi.axil_slave import AxiLiteSlave
from modules.vendor.glasgow_i2c.i2c import I2CInitiator
from util.nmigen import generate_states


class AxiLiteI2c(Elaboratable):
    def __init__(self, pads, clock_divider, base_address, address_bytes):
        self.addr_bytes = address_bytes
        self.clock_divider = clock_divider
        self.pads = pads

        self.i2c = I2CInitiator(self.pads, period_cyc=self.clock_divider)
        self.axi = AxiLiteSlave(
            address_range=range(base_address, base_address + 2 ** (8 * address_bytes)),
            handle_read=self.handle_read,
            handle_write=self.handle_write
        )
        self.bus = self.axi.bus

    def elaborate(self, platform):
        m = Module()

        m.submodules.axi = self.axi
        m.submodules.i2c = self.i2c

        return m

    def handle_read(self, m, addr, data, resp, read_done):
        i2c = self.i2c
        with m.FSM():
            with m.State("initial"):
                with m.If(~i2c.busy):
                    m.d.comb += i2c.start.eq(1)
                    m.next = "address_0"

            for i, state, next_state in generate_states("address_{}", self.addr_bytes, "data_0"):
                with m.State(state):
                    with m.FSM():
                        with m.State("wait"):
                            with m.If(~i2c.busy):
                                m.next = "write"
                            with m.State("write"):
                                m.d.comb += i2c.data_i.eq(addr[i * 8:(i + 1) * 8])
                        m.next = next_state

            for i, state, next_state in generate_states("data_{}", self.bus.data_bits // 8, "end"):
                with m.State(state):
                    with m.If(~i2c.busy):
                        m.d.comb += data[i * 8:(i + 1) * 8].eq(i2c.data_o)
                        m.next = next_state

            with m.State("end"):
                m.d.comb += i2c.stop.eq(1)
                m.d.sync += resp.eq(Response.OKAY)
                read_done()

    def handle_write(self, m, addr, data, resp, write_done):
        i2c = self.i2c
        with m.FSM():
            with m.State("initial"):
                with m.If(~i2c.busy):
                    m.d.comb += i2c.start.eq(1)
                    m.next = "address_0"

            for i, state, next_state in generate_states("address_{}", self.addr_bytes, "data_0"):
                with m.State(state):
                    with m.If(~i2c.busy):
                        m.d.comb += i2c.data_i.eq(addr[i*8:(i+1)*8])
                        m.next = next_state

            for i, state, next_state in generate_states("data_{}", self.bus.data_bits // 8, "end"):
                with m.State(state):
                    with m.If(~i2c.busy):
                        m.d.comb += i2c.data_i.eq(data[i * 8:(i + 1) * 8])
                        m.next = next_state

            with m.State("end"):
                m.d.comb += i2c.stop.eq(1)
                m.d.sync += resp.eq(Response.OKAY)
                write_done()
