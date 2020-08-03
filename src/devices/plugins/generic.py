from nmigen.build import *


def generic_plugin_connect(platform, plugin_number):
    platform.add_resources([
        Resource("generic_plugin", plugin_number,
             Subsignal("lvds", DiffPairs("lvds0_p lvds1_p lvds2_p lvds3_p lvds4_p lvds5_p",
                                         "lvds0_n lvds1_n lvds2_n lvds3_n lvds4_n lvds5_n",
                                         dir='io', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVDS_25")),
             Subsignal("gpio0", Pins("gpio0", conn=("plugin", plugin_number), dir="io"), Attrs(IOSTANDARD="LVCMOS25")),
             Subsignal("gpio1", Pins("gpio1", conn=("plugin", plugin_number), dir="io"), Attrs(IOSTANDARD="LVCMOS25")),
             Subsignal("gpio2", Pins("gpio2", conn=("plugin", plugin_number), dir="io"), Attrs(IOSTANDARD="LVCMOS25")),
             Subsignal("gpio3", Pins("gpio3", conn=("plugin", plugin_number), dir="io"), Attrs(IOSTANDARD="LVCMOS25")),
             Subsignal("gpio4", Pins("gpio4", conn=("plugin", plugin_number), dir="io"), Attrs(IOSTANDARD="LVCMOS25")),
             Subsignal("gpio5", Pins("gpio5", conn=("plugin", plugin_number), dir="io"), Attrs(IOSTANDARD="LVCMOS25")),
             Subsignal("gpio6", Pins("gpio6", conn=("plugin", plugin_number), dir="io"), Attrs(IOSTANDARD="LVCMOS25")),
             Subsignal("gpio7", Pins("gpio7", conn=("plugin", plugin_number), dir="io"), Attrs(IOSTANDARD="LVCMOS25")),
             Subsignal("i2c",
                Subsignal("scl", Pins("i2c_scl", conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS25")),
                Subsignal("sda", Pins("i2c_sda", conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS25")),
             )
        )
    ])
