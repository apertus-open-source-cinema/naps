from nmigen import *
from nmigen.back import rtlil, verilog, pysim
from nmigen.hdl.rec import Direction
from enum import Enum

# class AxiChannel:
#     def __init__(self, payload):
#         self.payload = payload
#         self.valid = Signal()
#         self.ready = Signal()
#
#
# class AxiChannelSink:
#     def elaborate(self):
#
#
# class AxiChannelSource:
#     def elaborate(self):


class Response(Enum):
    OKAY   = 0b00
    EXOKAY = 0b01
    SLVERR = 0b10
    DECERR = 0b11

class BurstType(Enum):
    FIXED = 0b00
    INCR  = 0b01
    WRAP  = 0b10


# TODO(robin): are these directions right????

def axi_channel(payload, master_to_slave):
    if master_to_slave:
        return payload + [("valid", 1, Direction.FANIN), ("ready", 1, Direction.FANOUT)]
    else:
        return payload + [("valid", 1, Direction.FANOUT), ("ready", 1, Direction.FANIN)]

# read address or write address channel
def address_channel(*, addr_bits, lite, id_bits):
    layout = axi_channel([
        ("addr", addr_bits, Direction.FANIN),
    ], True)

    if not lite:
        layout += [
            ("id", id_bits, Direction.FANIN),
            ("burst", 2, Direction.FANIN),
            ("len", 4, Direction.FANIN),
            ("size", 2, Direction.FANIN),
            ("prot", 3, Direction.FANIN)
        ]

    return layout

# read data or write data channel (for read data channel set read to true)
def data_channel(*, data_bits, lite, read, id_bits):
    direction = [Direction.FANIN, Direction.FANOUT]

    if read:
        direction = direction[::-1]

    if lite:
        assert data_bits == 32, "xilinx zynq only support 32bit data widths in axi lite mode"

    layout = axi_channel([
        ("data", data_bits, direction[0]),
    ], ~read)

    if read:
        layout += [("resp", 2, direction[0])]
    else:
        ("strb", 4, direction[0]) # slaves can elect to ignore strobe in axi lite

    if not lite:
        layout += [
            ("id", id_bits, direction[0]),
            ("last", 1, direction[0]),
        ]

    return layout

def write_response_channel(*, lite, id_bits):
    layout = axi_channel([
        ("resp", 2, Direction.FANOUT)
    ], False)

    if not lite:
        layout += [
            ("id", id_bits, Direction.FANOUT),
        ]

    return layout

class Interface(Record):
    def __init__(self, *, addr_bits, data_bits, lite, id_bits):
        layout = [
            ("read_address", address_channel(addr_bits=addr_bits, lite=lite, id_bits=id_bits)),
            ("write_address", address_channel(addr_bits=addr_bits, lite=lite, id_bits=id_bits)),
            ("read_data", data_channel(data_bits=data_bits, read=True, lite=lite, id_bits=id_bits)),
            ("write_data", data_channel(data_bits=data_bits, read=False, lite=lite, id_bits=id_bits)),
            ("write_response", write_response_channel(lite=lite, id_bits=id_bits)),
        ]

        super().__init__(layout, src_loc_at=1)


class AxiLiteSlaveToFullBridge(Elaboratable):
    def __init__(self):
        self.lite_bus = Interface(addr_bits = 32, data_bits = 32, lite = True, id_bits = 12)
        self.full_bus = Interface(addr_bits = 32, data_bits = 32, lite = False, id_bits = 12)

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.full_bus.connect(self.lite_bus)

        read_id = Signal.like(self.full_bus.read_data.id)
        write_id = Signal.like(self.full_bus.write_data.id)

        with m.If(self.full_bus.read_address.valid):
            m.d.comb += self.full_bus.read_data.id.eq(self.full_bus.read_address.id)
            m.d.sync += read_id.eq(self.full_bus.read_address.id)
        with m.Else():
            m.d.comb += self.full_bus.read_data.id.eq(read_id)

        with m.If(self.full_bus.write_address.valid):
            m.d.comb += self.full_bus.write_data.id.eq(self.full_bus.write_address.id)
            m.d.sync += write_id.eq(self.full_bus.write_address.id)
        with m.Else():
            m.d.comb += self.full_bus.write_data.id.eq(write_id)


        m.d.comb += self.full_bus.read_data.last.eq(1)

        return m


class AxiLiteSlave(Elaboratable):
    def __init__(self, read_done, write_done, handle_read, handle_write):
        self.bus = Interface(addr_bits = 32, data_bits = 32, lite = True, id_bits = 12) # 12 id bits for zynq
        self.read_done = read_done
        self.write_done = write_done
        self.handle_read = handle_read
        self.handle_write = handle_write
    def elaborate(self, platform):
        m = Module()

        addr = Signal.like(self.bus.read_address.addr)

        # read state machine
        with m.FSM() as fsm:
            with m.State("IDLE"):
                m.d.comb += self.bus.read_address.ready.eq(1)
                m.d.comb += self.bus.write_address.ready.eq(1)

                with m.If(self.bus.read_address.valid):
                    m.d.sync += addr.eq(self.bus.read_address.addr)
                    m.next = "READ"
                with m.Elif(self.bus.write_address.valid):
                    m.d.sync += addr.eq(self.bus.write_address.addr)
                    m.next = "WRITE"
            with m.State("READ"):
                self.handle_read(m, addr, self.bus.read_data.data, self.bus.read_data.resp)
                with m.If(self.read_done):
                    m.d.sync += self.read_done.eq(0)
                    m.next = "READ_DONE"
            with m.State("READ_DONE"):
                m.d.comb += self.bus.read_data.valid.eq(1)

                with m.If(self.bus.read_data.ready):
                    m.next = "IDLE"
            with m.State("WRITE"):
                with m.If(self.bus.write_data.valid):
                    self.handle_write(m, addr, self.bus.write_data.data, self.bus.write_response.resp)
                    with m.If(self.write_done):
                        m.d.sync += self.write_done.eq(0)
                        m.next = "WRITE_DONE"
            with m.State("WRITE_DONE"):
                m.d.comb += self.bus.write_response.valid.eq(1)
                with m.If(self.bus.write_response.ready):
                    m.next = "IDLE"

        return m

class AxiGPIO(Elaboratable):
    def __init__(self, pins):
        self.pins = pins

        read_done = Signal()
        write_done = Signal()

        def handle_read(m, addr, data, resp):
            pass
            m.d.sync += self.pins.bit_select(addr[30:], 1).eq(data[0])
            m.d.sync += resp.eq(Response.OKAY)
            m.d.sync += read_done.eq(1)

        def handle_write(m, addr, data, resp):
            pass
            m.d.sync += data[0].eq(self.pins.bit_select(addr[30:], 1))
            m.d.sync += resp.eq(Response.OKAY)
            m.d.sync += write_done.eq(1)

        self.axi_slave = AxiLiteSlave(read_done, write_done, handle_read, handle_write)

    def elaborate(self, platform):
        m = Module()

        m.submodules += self.axi_slave

        return m

pins = Signal(8)

print(verilog.convert(AxiGPIO(pins)))
