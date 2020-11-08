# TODO: finish
# TODO: add tests
# TODO: port to new register infrastructure

from nmigen import *

from .glasgow_i2c import I2CInitiator
from nmigen.lib.fifo import SyncFIFO, Rose

from lib.peripherals.csr_bank import StatusSignal, ControlSignal, EventReg


class I2cXilinx(Elaboratable):
    def __init__(self, axil_master, pads, base_address, gpo_width=0):
        """ A axil i2c peripheral meant to be compatible with the Xilinx IIC linux kernel pydriver.
        see https://japan.xilinx.com/support/documentation/ip_documentation/axi_iic/v2_0/pg090-axi-iic.pdf for register
        map. Currently only the I2C master functionality is implemented.

        :param pads: the i2c pads as requested as a nmigen resource.
        :param base_address: the base address of the axil peripheral.
        :param axil_master: the axil master to which this peripheral is attached.
        """
        self.interrupt = StatusSignal()

        self._axil_master = axil_master
        self.pads = pads
        self._base_address = base_address

        self.i2c : I2CInitiator = DomainRenamer("i2c")(I2CInitiator(self.pads, period_cyc=1))

        ### registers ###

        self.global_interrupt_enable = ControlSignal(address="0x01C:31", reset=0)

        self.interrupt_tx_fifo_half_empty = StatusSignal(address="0x020:7", reset=1)
        self.interrupt_not_addressed_as_slave = StatusSignal(address="0x020:6", reset=1)
        self.interrupt_addressed_as_slave = StatusSignal(address="0x020:5", reset=0)
        self.interrupt_bus_not_busy = StatusSignal(address="0x020:4", reset=0)
        self.interrupt_rx_fifo_full = StatusSignal(address="0x020:3", reset=0)
        self.interrupt_tx_fifo_empty = StatusSignal(address="0x020:2", reset=0)
        self.interrupt_tx_error_slave_tx_comp = StatusSignal(address="0x020:1", reset=0)
        self.interrupt_arb_lost = StatusSignal(address="0x020:0", reset=0)

        self.ien_tx_fifo_half_empty = ControlSignal(address="0x028:7")
        self.ien_not_addressed_as_slave = ControlSignal(address="0x028:6")
        self.ien_addressed_as_slave = ControlSignal(address="0x028:5")
        self.ien_bus_not_busy = ControlSignal(address="0x028:4")
        self.ien_rx_fifo_full = ControlSignal(address="0x028:3")
        self.ien_tx_fifo_empty = ControlSignal(address="0x028:2")
        self.ien_tx_error_slave_tx_comp = ControlSignal(address="0x028:1")
        self.ien_arb_lost = ControlSignal(address="0x028:0")

        self.reset = EventReg("0x040:3-0")

        self.cr_general_call_enable = ControlSignal(address="0x100:6")
        self.cr_repeated_start = ControlSignal(address="0x100:5")
        self.cr_transmit_acknowledge_enable = ControlSignal(address="0x100:4")
        self.cr_transmit_receive_mode_select = ControlSignal(address="0x100:3")
        self.cr_master_slave_mode_select = ControlSignal(address="0x100:2")
        self.cr_transmit_fifo_reset = ControlSignal(address="0x100:1")
        self.cr_axi_iic_enable = ControlSignal(address="0x100:0")

        self.status_tx_fifo_empty = StatusSignal(address="0x104:7")
        self.status_rx_fifo_empty = StatusSignal(address="0x104:6")
        self.status_rx_fifo_full = StatusSignal(address="0x104:5")
        self.status_tx_fifo_full = StatusSignal(address="0x104:4")
        self.status_slave_read_write = StatusSignal(address="0x104:3")
        self.status_bus_busy = StatusSignal(address="0x104:2")
        self.status_adressed_as_slave = StatusSignal(address="0x104:1")
        self.status_adressed_by_general_call = StatusSignal(address="0x104:0")

        self.tx_fifo_data_start_stop = EventReg("0x108:9-0")

        self.rx_fifo_data = EventReg("0x10C:7-0")

        self.slave_address = ControlSignal(address="0x110:7-1")  # ignored
        self.slave_ten_bit_address_addition = ControlSignal(address="0x11C:2-0")  # ignored

        self.tx_fifo_occupancy = StatusSignal(address="0x114:3-0")

        self.rx_fifo_programmable_depth_interrupt = ControlSignal(address="0x120:3-0")

        self.general_purpose_output_register = ControlSignal(address="0x124:{}-0".format(gpo_width))  # kind of an odd feature

        self.timing_tsusta = ControlSignal(address="0x128")
        self.timing_tsusto = ControlSignal(address="0x12C")
        self.timing_thdsta = ControlSignal(address="0x130")
        self.timing_tsudat = ControlSignal(address="0x134")
        self.timing_tbuf = ControlSignal(address="0x138")
        self.timing_thigh = ControlSignal(address="0x13C")
        self.timing_tlow = ControlSignal(address="0x140")
        self.timing_thddat = ControlSignal(address="0x140")

    def elaborate(self, platform):
        m = Module()

        m.domains += ClockDomain("i2c")
        m.d.comb += ClockSignal("i2c").eq(ClockSignal())

        rx_fifo = m.submodules.rx_fifo = SyncFIFO(width=8, depth=2 ** 4, fwft=False)
        tx_fifo = m.submodules.tx_fifo = SyncFIFO(width=10, depth=2 ** 4, fwft=False)

        m.d.comb += self.tx_fifo_occupancy.eq(tx_fifo.level)
        m.d.comb += self.status_tx_fifo_empty.eq(tx_fifo.level == 0)
        m.d.comb += self.status_tx_fifo_full.eq(tx_fifo.level == tx_fifo.depth - 1)

        m.d.comb += self.status_rx_fifo_empty.eq(rx_fifo.level == 0)
        m.d.comb += self.status_rx_fifo_full.eq(rx_fifo.level == rx_fifo.depth - 1)

        m.d.comb += self.status_bus_busy.eq(self.i2c.busy)
        m.d.comb += self.interrupt_bus_not_busy.eq(~self.i2c.busy)

        def on_rx_fifo_read():
            m.d.comb += rx_fifo.r_en.eq(1)
            return rx_fifo.r_data

        self.rx_fifo_data.on_read = on_rx_fifo_read

        def on_tx_fifo_write(write_data):
            m.d.comb += tx_fifo.w_en.eq(1)
            m.d.comb += tx_fifo.w_data.eq(write_data)

        self.tx_fifo_data_start_stop = on_tx_fifo_write

        m.d.comb += self.tx_fifo_occupancy.eq(tx_fifo.level)

        m.d.comb += self.interrupt_tx_fifo_half_empty.eq(tx_fifo.level[-1])
        m.d.comb += self.interrupt_tx_fifo_empty.eq(tx_fifo.level == 0)
        m.d.comb += self.interrupt_rx_fifo_full.eq(
            rx_fifo.level >= self.rx_fifo_programmable_depth_interrupt)

        # we use an edge triggered interrupt here
        m.d.comb += self.interrupt.eq([
            Rose(getattr(self, "interrupt_{}".format(name))) & getattr(self, "ien_{}".format(name))
            for name in dir(self) if name.startswith("interrupt")
        ])

        def on_reset_write(write_data):
            with m.If(write_data == 0xA):  # 0xA is the magic key here, idk why this is implemented in such a wired way
                m.d.comb += ResetSignal("i2c").eq(1)
        self.reset.on_write = on_reset_write

        return m
