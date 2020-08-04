# the usb3 plugin module plugin module resource
# (not the platform definition for building gateware for the fpga _on_ the plugin module itself)
# see: https://wiki.apertus.org/index.php/1x_USB_3.0_Plugin_Module

from nmigen.build import *


def usb3_plugin_connect(platform, plugin_number):
    platform.add_resources([
        Resource("usb3_plugin", plugin_number,
             Subsignal("lvds", DiffPairs("lvds0_p lvds1_p lvds2_p lvds3_p lvds4_p lvds5_p",
                                         "lvds0_n lvds1_n lvds2_n lvds3_n lvds4_n lvds5_n",
                                         dir='io', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="DIFF_SSTL18_I")),
             Subsignal("jtag",
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
