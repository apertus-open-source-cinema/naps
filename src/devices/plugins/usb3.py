# the usb3 plugin module plugin module resource
# (not the platform definition for building gateware for the fpga _on_ the plugin module itself)
# see: https://wiki.apertus.org/index.php/1x_USB_3.0_Plugin_Module

from nmigen.build import *


def usb3_plugin_connect(platform, plugin_number):
    platform.add_resources([
        Resource(
            "usb3_plugin", plugin_number,

            Subsignal("lvds0", DiffPairs("lvds0_p", "lvds0_n", dir='o', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="DIFF_SSTL18_I")),
            Subsignal("lvds1", DiffPairs("lvds1_p", "lvds1_n", dir='o', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="DIFF_SSTL18_I")),
            Subsignal("lvds2", DiffPairs("lvds2_p", "lvds2_n", dir='o', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="DIFF_SSTL18_I")),
            Subsignal("lvds3", DiffPairs("lvds3_p", "lvds3_n", dir='o', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="DIFF_SSTL18_I")),
            Subsignal("valid", Pins("lvds4_n", dir='o', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS18")),
            Subsignal("ready", Pins("lvds4_p", dir='o', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS18")),
            Subsignal("clk_word", DiffPairs("lvds5_p", "lvds5_n", dir='o', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="DIFF_SSTL18_I")),

            Subsignal(
                "jtag",
                Subsignal("tms", Pins("gpio0", dir="o", conn=("plugin", plugin_number))),
                Subsignal("tck", Pins("gpio1", dir="o", conn=("plugin", plugin_number))),
                Subsignal("tdi", Pins("gpio2", dir="o", conn=("plugin", plugin_number))),
                Subsignal("tdo", Pins("gpio3", dir="i", conn=("plugin", plugin_number))),
            ),
            Subsignal("jtag_enb", Pins("gpio4", dir="o", conn=("plugin", plugin_number))),
            Subsignal("program", PinsN("gpio5", dir="o", conn=("plugin", plugin_number))),
            Subsignal("init", PinsN("gpio6", dir="o", conn=("plugin", plugin_number))),
            Subsignal("done", PinsN("gpio7", dir="i", conn=("plugin", plugin_number))),
        )
    ])
