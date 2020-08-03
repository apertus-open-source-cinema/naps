from nmigen.build import *


def generic_plugin_connect(platform, plugin_number):
    platform.add_resources([
        Resource("generic_plugin", plugin_number,
             Subsignal("lvds", DiffPairs("lvds0_p lvds1_p lvds2_p lvds3_p lvds4_p lvds5_p",
                                         "lvds0_n lvds1_n lvds2_n lvds3_n lvds4_n lvds5_n",
                                         dir='io', conn=("plugin", plugin_number)), Attrs(IOSTANDARD="DIFF_SSTL18_I")),
             Subsignal("gpio", Pins("gpio0 gpio1 gpio2 gpio3 gpio4 gpio5 gpio6 gpio7", conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS33")),
             Subsignal("i2c",
                Subsignal("scl", Pins("i2c_scl", conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS33")),
                Subsignal("sda", Pins("i2c_sda", conn=("plugin", plugin_number)), Attrs(IOSTANDARD="LVCMOS33")),
             )
        )
    ])
