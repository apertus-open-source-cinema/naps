import unittest
from nmigen import *
from naps import Response, SimPlatform
from naps.vendor import JTAG
from .jtag_peripheral_connector import JTAGPeripheralConnector


class DummyPeripheral(Elaboratable):
    def range(self):
        return range(0, 1024)

    def __init__(self):
        self.mem = Memory(width=32, depth=1024, init=list(range(1024)))
        self.read_port = self.mem.read_port()
        self.write_port = self.mem.write_port()

        self.read_ctr = Signal(range(10))
        self.write_ctr = Signal(range(10))

    def elaborate(self, platform):
        m = Module()
        m.submodules.read_port = self.read_port
        m.submodules.write_port = self.write_port

        m.d.comb += Signal().eq(self.read_ctr)
        m.d.comb += Signal().eq(self.write_ctr)
        return m

    def handle_read(self, m, addr, data, read_done):
        with m.If(addr < 1024):
            m.d.sync += self.read_ctr.eq(self.read_ctr + 1)
            m.d.sync += self.read_port.addr.eq(addr)
            with m.If(self.read_ctr == 5):
                m.d.sync += data.eq(self.read_port.data)
                m.d.sync += self.read_ctr.eq(0)
                read_done(Response.OK)
        with m.Else():
            read_done(Response.ERR)

    def handle_write(self, m, addr, data, write_done):
        with m.If(addr < 1024):
            m.d.sync += self.write_ctr.eq(self.write_ctr + 1)
            m.d.sync += self.write_port.addr.eq(addr)
            with m.If(self.write_ctr == 5):
                m.d.comb += self.write_port.data.eq(data)
                m.d.comb += self.write_port.en.eq(1)
                m.d.sync += self.write_ctr.eq(0)
                write_done(Response.OK)
        with m.Else():
            write_done(Response.ERR)


class TestJTAGPeripheralConnectorFSM(unittest.TestCase):
    def check_read_write(self, tdi_delay=0, tdo_delay=0):
        platform = SimPlatform()

        jtag_device = JTAG()
        m = Module()
        test_peripheral = m.submodules.test_peripheral = DummyPeripheral()
        m.submodules.jtag = JTAGPeripheralConnector(test_peripheral, jtag_device, jtag_domain="sync")

        jtag_testbench = JTAG()
        jtag_device.shift_tdi = jtag_testbench.shift_tdi
        jtag_device.shift_tdo = jtag_testbench.shift_tdi
        if tdi_delay == 0:
            jtag_device.tdi = jtag_testbench.tdi
        else:
            tdi_delay_chain = [jtag_device.tdi] + [Signal() for _ in range(tdi_delay - 1)] + [jtag_testbench.tdi]
            for src, dst in zip(tdi_delay_chain[1:], tdi_delay_chain[:-1]):
                m.d.sync += dst.eq(src)
        if tdo_delay == 0:
            jtag_device.tdo = jtag_testbench.tdo
        else:
            tdo_delay_chain = [jtag_testbench.tdo] + [Signal() for _ in range(tdo_delay - 1)] + [jtag_device.tdo]
            for src, dst in zip(tdo_delay_chain[1:], tdo_delay_chain[:-1]):
                m.d.sync += dst.eq(src)

        result = 0

        def shift_word(value, width=32):
            yield jtag_testbench.shift_tdi.eq(1)
            result_str = ""
            output_string = list(reversed("{{:0{}b}}".format(width).format(value)))
            for bit in output_string:
                if bit == "1":
                    yield jtag_testbench.tdi.eq(1)
                else:
                    yield jtag_testbench.tdi.eq(0)
                result_str += str((yield jtag_testbench.tdo))
                yield
            global result
            result = int("".join(reversed(result_str)), 2)
            yield jtag_testbench.shift_tdi.eq(0)

        def shift_bit(value):
            yield from shift_word(value, width=1)

        def testbench():
            fsm = platform.fragment.subfragments[1][0].find_generated("fsm")
            global result

            def assert_state(desired_state):
                if tdi_delay == 0 and tdo_delay == 0:
                    assert fsm.decoding[(yield fsm.state)] == desired_state

            def write(addr, value):
                for _ in range(10):
                    yield
                yield from shift_bit(0)  # wakeup
                yield from shift_bit(1)  # wakeup
                yield from assert_state("IDLE1")
                yield from shift_word(addr)  # address
                yield from assert_state("ADDR31")
                yield from shift_bit(1)  # write
                yield from assert_state("RW_CMD")
                yield from shift_word(value)
                yield from assert_state("WRITE31")
                # read wait
                timeout = 100
                for t in range(timeout):
                    if t == 0:
                        yield from assert_state("WRITE31")
                    else:
                        yield from assert_state("WRITE_WAIT")
                    yield from shift_bit(1)
                    if result == 1:
                        break
                    if t == timeout - 1:
                        raise TimeoutError()
                yield from assert_state("WRITE_STATUS")
                yield from shift_bit(0)  # read status
                assert result == 0
                yield from assert_state("IDLE0")

            def read(addr, expected_value):
                for _ in range(10):
                    yield
                yield from shift_bit(0)  # wakeup
                yield from shift_bit(1)  # wakeup
                yield from assert_state("IDLE1")
                yield from shift_word(addr)  # address
                yield from assert_state("ADDR31")
                yield from shift_bit(0)  # read
                yield from assert_state("RW_CMD")
                # read wait
                timeout = 100
                for t in range(timeout):
                    if t == 0:
                        yield from assert_state("RW_CMD")
                    else:
                        yield from assert_state("READ_WAIT")
                    yield from shift_bit(1)
                    if result == 1:
                        break
                    if t == timeout - 1:
                        raise TimeoutError()
                yield from assert_state("READ0")
                yield from shift_word(0)
                assert result == expected_value
                yield from assert_state("READ_STATUS")
                yield from shift_bit(0)  # read status
                assert result == 0
                yield from assert_state("IDLE0")

            for addr in range(0, 100, 10):
                yield from write(addr, addr + 1)
            for addr in range(0, 100, 10):
                yield from read(addr, addr + 1)

        platform.add_sim_clock("sync", 100e6)
        platform.sim(m, testbench)

    def test_read_transaction(self):
        self.check_read_write()

    def test_read_transaction_tdi_delay(self):
        self.check_read_write(tdi_delay=1, tdo_delay=0)

    def test_read_transaction_tdo_delay(self):
        self.check_read_write(tdi_delay=0, tdo_delay=1)

    def test_read_transaction_delay(self):
        self.check_read_write(tdi_delay=10, tdo_delay=10)
