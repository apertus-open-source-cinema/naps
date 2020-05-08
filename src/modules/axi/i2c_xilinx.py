from nmigen import *

from modules.axi.static_csr import Direction, Reg, EventReg
from modules.vendor.glasgow_i2c.i2c import I2CInitiator


class Registers:
    global_interrupt_enable = Reg("0x01C:31", Direction.RW, reset=0)

    interrupt_tx_fifo_half_empty = Reg("0x020:7", Direction.R, reset=1)
    interrupt_not_addressed_as_slave = Reg("0x020:6", Direction.R, reset=1)
    interrupt_addressed_as_slave = Reg("0x020:5", Direction.R, reset=0)
    interrupt_bus_not_busy = Reg("0x020:4", Direction.R, reset=0)
    interrupt_rx_fifo_full_empty = Reg("0x020:3", Direction.R, reset=0)
    interrupt_tx_fifo_empty = Reg("0x020:2", Direction.R, reset=0)
    interrupt_tx_error_slave_tx_comp = Reg("0x020:1", Direction.R, reset=0)
    interrupt_arb_lost = Reg("0x020:0", Direction.R, reset=0)

    ien_tx_fifo_half_empty = Reg("0x028:7", Direction.RW)
    ien_not_addressed_as_slave = Reg("0x028:6", Direction.RW)
    ien_addressed_as_slave = Reg("0x028:5", Direction.RW)
    ien_bus_not_busy = Reg("0x028:4", Direction.RW)
    ien_rx_fifo_full_empty = Reg("0x028:3", Direction.RW)
    ien_tx_fifo_empty = Reg("0x028:2", Direction.RW)
    ien_tx_error_slave_tx_comp = Reg("0x028:1", Direction.RW)
    ien_arb_lost = Reg("0x028:0", Direction.RW)

    reset = EventReg("0x040:3-0")

    cr_general_call_enable = Reg("0x100:6", Direction.RW)
    cr_repeated_start = Reg("0x100:5", Direction.RW)
    cr_transmit_acknowledge_enable = Reg("0x100:4", Direction.RW)
    cr_transmit_receive_mode_select = Reg("0x100:3", Direction.RW)
    cr_master_slave_mode_select = Reg("0x100:2", Direction.RW)
    cr_transmit_fifo_reset = Reg("0x100:1", Direction.RW)
    cr_axi_iic_enable = Reg("0x100:0", Direction.RW)

    status_tx_fifo_empty = Reg("0x104:7", Direction.R)
    status_rx_fifo_empty = Reg("0x104:6", Direction.R)
    status_rx_fifo_full = Reg("0x104:5", Direction.R)
    status_tx_fifo_full = Reg("0x104:4", Direction.R)
    status_slave_read_write = Reg("0x104:3", Direction.R)
    status_bus_busy = Reg("0x104:2", Direction.R)
    status_adressed_as_slave = Reg("0x104:1", Direction.R)
    status_adressed_by_general_call = Reg("0x104:0", Direction.R)

    tx_fifo_stop = EventReg("0x108:9")
    tx_fifo_start = EventReg("0x108:8")
    tx_fifo_data = EventReg("0x108:7-0")

    rx_fifo_data = EventReg("0x10C:7-0")

    slave_address = Reg("0x110:7-1", Direction.RW)
    slave_ten_bit_address_addition = Reg("0x11C:2-0",
                                         Direction.RW)  # this is a kind of odd adress, maybe an afterthougth?

    tx_fifo_occupancy = Reg("0x114:3-0", Direction.R)

    rx_fifo_programmable_depth_interrupt = Reg("0x120:3-0", Direction.RW)

    def __init__(self, gpo_width):
        general_purpose_output_register = Reg("0x124:{}-0".format(gpo_width), Direction.RW)  # kind of an odd feature

    timing_tsusta = Reg("0x128", Direction.RW)
    timing_tsusto = Reg("0x12C", Direction.RW)
    timing_thdsta = Reg("0x130", Direction.RW)
    timing_tsudat = Reg("0x134", Direction.RW)
    timing_tbuf = Reg("0x138", Direction.RW)
    timing_thigh = Reg("0x13C", Direction.RW)
    timing_tlow = Reg("0x140", Direction.RW)
    timing_thddat = Reg("0x140", Direction.RW)


class AxiLiteI2c(Elaboratable):
    def __init__(self, axil_master, pads, base_address, gpo_width=0):
        """ A axil i2c master meant to be compatible with the Xilinx IIC linux kernel driver.
        see https://japan.xilinx.com/support/documentation/ip_documentation/axi_iic/v2_0/pg090-axi-iic.pdf for register
        map.

        :param pads: the i2c pads as requested as a nmigen resource.
        :param base_address: the base address of the axil peripheral.
        :param axil_master: the axil master to which this peripheral is attached.
        """
        self.axil_master = axil_master
        self.pads = pads
        self.base_address = base_address

        self.registers = Registers(gpo_width)

        self.i2c = I2CInitiator(self.pads, period_cyc=1)

    def elaborate(self, platform):
        m = Module()

        m.submodules.axi_slave = self.axi_slave
        m.submodules.i2c = self.i2c

        return m
