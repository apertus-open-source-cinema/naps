""" Generates a pin mapping constraints file for the axiom micro
"""

from nmigen import *
import pandas as pd
import sys
import os
import re

sys.path.append(os.path.realpath("src"))
os.chdir(os.path.dirname(__file__))
from top import Top


def unwrap(df):
    assert df.size == 1
    return df.values[0]


micro_mapping = pd.read_csv("micro_r2.csv", skip_blank_lines=True, comment='#')


def get_net_by_signal(signal):
    signal = signal.replace("__", ".")
    bank_io = micro_mapping[micro_mapping.name == signal].bank_io
    try:
        return unwrap(bank_io)
    except AssertionError:
        if bank_io.size == 0:
            raise IndexError("Signal {} not found in mapping.".format(signal))
        else:
            raise IndexError("Signal {} is mapped to multiple locations: {}".format(signal, bank_io))


z_turn_lite_mapping = pd.read_csv("z_turn_lite.csv", skip_blank_lines=True, comment='#')


def get_pin_by_net_name(net_name):
    (bank, index, polarity) = re.match("(\d{2})_(\d{1,2})([pn]?)", net_name).groups()
    polarity = polarity or "P"
    net_name = "IO_B{}_L{}{}".format(bank, polarity.upper(), index)
    row = z_turn_lite_mapping[z_turn_lite_mapping.net_name == net_name]
    return unwrap(row.fpga_pin)


def get_io_standart(net_name):
    (bank, index, polarity) = re.match("(\d{2})_(\d{1,2})([pn]?)", net_name).groups()
    if polarity:
        return "LVCMOS18"  # single ended signals
    else:
        return "DIFF_SSTL18_I"  # LVDS signals


if __name__ == "__main__":
    print("set_property -dict { PACKAGE_PIN %s IOSTANDARD %s } [get_ports { %s }]; " % (
        "B10", "LVCMOS33", "rst"))
    print("set_property -dict { PACKAGE_PIN %s IOSTANDARD %s } [get_ports { %s }]; " % (
        "E7", "LVCMOS33", "clk"))
    print('create_clock -name clk -period "10" [get_pins "E7"]; \nset_input_jitter clk 0.3;')

    top = Top()
    ports = top.get_ports()
    for port in ports:
        if port.nbits == 1:
            net = get_net_by_signal(port.name)
            fpga_pin = get_pin_by_net_name(net)
            io_standard = get_io_standart(net)
            print("set_property -dict { PACKAGE_PIN %s IOSTANDARD %s } [get_ports { %s }]; " % (
            fpga_pin, io_standard, port.name))
        else:
            for i in range(port.nbits):
                name = port.name + "[%d]" % i
                net = get_net_by_signal(name)
                fpga_pin = get_pin_by_net_name(net)
                io_standard = get_io_standart(net)
                print("set_property -dict { PACKAGE_PIN %s IOSTANDARD %s } [get_ports { %s }]; " % (
                fpga_pin, io_standard, name))
